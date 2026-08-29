from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.service import AuditService
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.reconciliation_review import (
    ReconciliationOutcomeRecord,
    ReconciliationReviewActionRecord,
    ReconciliationReviewRecord,
)
from ledgerpilot.persistence.repositories.clients import ClientRepository
from ledgerpilot.persistence.repositories.reconciliation_review import (
    ReconciliationReviewRepository,
)
from ledgerpilot.reconciliation.states import (
    TERMINAL_RECONCILIATION_REVIEW_STATUSES,
    ReconciliationOutcomeType,
    ReconciliationReviewActionType,
    ReconciliationReviewStatus,
)


@dataclass(frozen=True)
class ReconciliationReviewHistory:
    review: ReconciliationReviewRecord
    actions: tuple[ReconciliationReviewActionRecord, ...]
    outcome: ReconciliationOutcomeRecord | None


class ReconciliationReviewService:
    def __init__(self, *, session: Session) -> None:
        self._session = session
        self._clients = ClientRepository(session)
        self._reviews = ReconciliationReviewRepository(session)
        self._audit = AuditService(session)

    def create_review(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        match_run_id: UUID,
        request_id: str | None,
    ) -> ReconciliationReviewRecord:
        self._require_client_access(principal=principal, client_id=client_id)
        self._lock_transaction(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        existing = self._reviews.get_review_for_transaction(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        if existing is not None:
            raise ApiError(
                status_code=409,
                code="reconciliation_review_exists",
                message="The bank transaction already has a reconciliation review.",
            )
        run = self._reviews.get_match_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            match_run_id=match_run_id,
        )
        if run is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")

        review = ReconciliationReviewRecord(
            id=uuid.uuid4(),
            bank_transaction_id=bank_transaction_id,
            firm_id=principal.firm_id,
            client_id=client_id,
            match_run_id=run.id,
            created_by_user_id=principal.user_id,
            created_by_membership_id=principal.membership_id,
            status=ReconciliationReviewStatus.OPEN.value,
            selected_review_outcome_id=None,
            request_id=request_id,
        )
        self._reviews.add_review(review)
        self._record_event(
            event_type=AuditEventType.RECONCILIATION_REVIEW_CREATED,
            principal=principal,
            review=review,
            request_id=request_id,
            metadata={"match_run_id": str(run.id)},
        )
        self._commit_or_raise(
            conflict_code="reconciliation_review_conflict",
            conflict_message="The reconciliation review conflicts with existing state.",
        )
        return review

    def get_review(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
    ) -> ReconciliationReviewRecord:
        self._require_client_access(principal=principal, client_id=client_id)
        review = self._reviews.get_review_for_transaction(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        if review is None or review.id != reconciliation_review_id:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return review

    def select_candidate(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
        review_outcome_id: UUID,
        request_id: str | None,
    ) -> ReconciliationReviewRecord:
        review = self._lock_review_context(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            reconciliation_review_id=reconciliation_review_id,
        )
        self._require_open(review)
        candidate = self._reviews.get_candidate_for_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            match_run_id=review.match_run_id,
            review_outcome_id=review_outcome_id,
        )
        if candidate is None:
            raise ApiError(
                status_code=422,
                code="candidate_not_in_review_match_run",
                message="The selected candidate does not belong to this reconciliation review.",
            )

        review.selected_review_outcome_id = candidate.review_outcome_id
        review.updated_at = datetime.now(UTC)
        self._add_action(
            principal=principal,
            review=review,
            action_type=ReconciliationReviewActionType.CANDIDATE_SELECTED,
            candidate_review_outcome_id=candidate.review_outcome_id,
            reason=None,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.RECONCILIATION_CANDIDATE_SELECTED,
            principal=principal,
            review=review,
            request_id=request_id,
            metadata={"review_outcome_id": str(candidate.review_outcome_id)},
        )
        self._commit_or_raise()
        return review

    def dispute(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
        reason: str,
        request_id: str | None,
    ) -> ReconciliationReviewRecord:
        normalized_reason = self._require_reason(
            reason,
            code="reconciliation_dispute_reason_required",
        )
        review = self._lock_review_context(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            reconciliation_review_id=reconciliation_review_id,
        )
        self._require_open(review)

        review.status = ReconciliationReviewStatus.DISPUTED.value
        review.updated_at = datetime.now(UTC)
        self._add_action(
            principal=principal,
            review=review,
            action_type=ReconciliationReviewActionType.DISPUTED,
            candidate_review_outcome_id=review.selected_review_outcome_id,
            reason=normalized_reason,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.RECONCILIATION_DISPUTED,
            principal=principal,
            review=review,
            request_id=request_id,
            metadata={"selected_review_outcome_id": _uuid_text(review.selected_review_outcome_id)},
        )
        self._commit_or_raise()
        return review

    def reopen(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
        reason: str,
        request_id: str | None,
    ) -> ReconciliationReviewRecord:
        normalized_reason = self._require_reason(
            reason,
            code="reconciliation_reopen_reason_required",
        )
        review = self._lock_review_context(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            reconciliation_review_id=reconciliation_review_id,
        )
        if review.status != ReconciliationReviewStatus.DISPUTED.value:
            raise ApiError(
                status_code=409,
                code="reconciliation_review_not_disputed",
                message="Only a disputed reconciliation review can be reopened.",
            )

        review.status = ReconciliationReviewStatus.OPEN.value
        review.updated_at = datetime.now(UTC)
        self._add_action(
            principal=principal,
            review=review,
            action_type=ReconciliationReviewActionType.REOPENED,
            candidate_review_outcome_id=review.selected_review_outcome_id,
            reason=normalized_reason,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.RECONCILIATION_DISPUTE_REOPENED,
            principal=principal,
            review=review,
            request_id=request_id,
            metadata={"selected_review_outcome_id": _uuid_text(review.selected_review_outcome_id)},
        )
        self._commit_or_raise()
        return review

    def approve_match(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
        note: str | None,
        request_id: str | None,
    ) -> tuple[ReconciliationReviewRecord, ReconciliationOutcomeRecord]:
        review = self._lock_review_context(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            reconciliation_review_id=reconciliation_review_id,
        )
        self._require_open(review)
        if review.selected_review_outcome_id is None:
            raise ApiError(
                status_code=409,
                code="reconciliation_candidate_required",
                message="A candidate must be selected before approving a reconciliation match.",
            )
        if (
            self._reviews.get_outcome_for_review(
                firm_id=principal.firm_id,
                client_id=client_id,
                reconciliation_review_id=review.id,
            )
            is not None
        ):
            raise ApiError(
                status_code=409,
                code="reconciliation_outcome_exists",
                message="The reconciliation review already has a terminal outcome.",
            )

        candidate = self._reviews.get_candidate_for_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            match_run_id=review.match_run_id,
            review_outcome_id=review.selected_review_outcome_id,
        )
        if candidate is None:
            raise ApiError(
                status_code=409,
                code="reconciliation_candidate_missing",
                message="The selected reconciliation candidate is no longer available.",
            )
        existing_match = self._reviews.get_matched_outcome_for_review_outcome(
            firm_id=principal.firm_id,
            client_id=client_id,
            review_outcome_id=candidate.review_outcome_id,
        )
        if existing_match is not None:
            raise ApiError(
                status_code=409,
                code="reconciliation_target_already_matched",
                message=(
                    "This approved accounting outcome is already reconciled to another transaction."
                ),
            )

        normalized_note = _optional_text(note)
        outcome = ReconciliationOutcomeRecord(
            id=uuid.uuid4(),
            reconciliation_review_id=review.id,
            bank_transaction_id=review.bank_transaction_id,
            firm_id=review.firm_id,
            client_id=review.client_id,
            match_run_id=review.match_run_id,
            matched_review_outcome_id=candidate.review_outcome_id,
            actor_user_id=principal.user_id,
            actor_membership_id=principal.membership_id,
            outcome_type=ReconciliationOutcomeType.MATCHED.value,
            reason=normalized_note,
            request_id=request_id,
        )
        self._reviews.add_outcome(outcome)
        review.status = ReconciliationReviewStatus.MATCHED.value
        review.updated_at = datetime.now(UTC)
        self._add_action(
            principal=principal,
            review=review,
            action_type=ReconciliationReviewActionType.APPROVED_MATCH,
            candidate_review_outcome_id=candidate.review_outcome_id,
            reason=normalized_note,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.RECONCILIATION_APPROVED,
            principal=principal,
            review=review,
            request_id=request_id,
            metadata={
                "outcome_id": str(outcome.id),
                "matched_review_outcome_id": str(candidate.review_outcome_id),
            },
        )
        self._commit_or_raise(
            conflict_code="reconciliation_terminal_conflict",
            conflict_message="The reconciliation outcome conflicts with existing terminal state.",
        )
        return review, outcome

    def mark_unmatched(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
        reason: str,
        request_id: str | None,
    ) -> tuple[ReconciliationReviewRecord, ReconciliationOutcomeRecord]:
        normalized_reason = self._require_reason(
            reason,
            code="reconciliation_unmatched_reason_required",
        )
        review = self._lock_review_context(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            reconciliation_review_id=reconciliation_review_id,
        )
        self._require_nonterminal(review)
        if (
            self._reviews.get_outcome_for_review(
                firm_id=principal.firm_id,
                client_id=client_id,
                reconciliation_review_id=review.id,
            )
            is not None
        ):
            raise ApiError(
                status_code=409,
                code="reconciliation_outcome_exists",
                message="The reconciliation review already has a terminal outcome.",
            )

        outcome = ReconciliationOutcomeRecord(
            id=uuid.uuid4(),
            reconciliation_review_id=review.id,
            bank_transaction_id=review.bank_transaction_id,
            firm_id=review.firm_id,
            client_id=review.client_id,
            match_run_id=review.match_run_id,
            matched_review_outcome_id=None,
            actor_user_id=principal.user_id,
            actor_membership_id=principal.membership_id,
            outcome_type=ReconciliationOutcomeType.UNMATCHED.value,
            reason=normalized_reason,
            request_id=request_id,
        )
        self._reviews.add_outcome(outcome)
        review.status = ReconciliationReviewStatus.UNMATCHED.value
        review.updated_at = datetime.now(UTC)
        self._add_action(
            principal=principal,
            review=review,
            action_type=ReconciliationReviewActionType.MARKED_UNMATCHED,
            candidate_review_outcome_id=review.selected_review_outcome_id,
            reason=normalized_reason,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.RECONCILIATION_MARKED_UNMATCHED,
            principal=principal,
            review=review,
            request_id=request_id,
            metadata={
                "outcome_id": str(outcome.id),
                "selected_review_outcome_id": _uuid_text(review.selected_review_outcome_id),
            },
        )
        self._commit_or_raise(
            conflict_code="reconciliation_terminal_conflict",
            conflict_message="The reconciliation outcome conflicts with existing terminal state.",
        )
        return review, outcome

    def history(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
    ) -> ReconciliationReviewHistory:
        review = self.get_review(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            reconciliation_review_id=reconciliation_review_id,
        )
        actions = tuple(
            self._reviews.list_actions(
                firm_id=principal.firm_id,
                client_id=client_id,
                reconciliation_review_id=review.id,
            )
        )
        outcome = self._reviews.get_outcome_for_review(
            firm_id=principal.firm_id,
            client_id=client_id,
            reconciliation_review_id=review.id,
        )
        return ReconciliationReviewHistory(review=review, actions=actions, outcome=outcome)

    def _lock_review_context(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
    ) -> ReconciliationReviewRecord:
        self._require_client_access(principal=principal, client_id=client_id)
        self._lock_transaction(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        review = self._reviews.lock_review(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            reconciliation_review_id=reconciliation_review_id,
        )
        if review is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return review

    def _lock_transaction(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
    ) -> None:
        transaction = self._reviews.lock_transaction(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        if transaction is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")

    def _require_client_access(self, *, principal: Principal, client_id: UUID) -> None:
        client = self._clients.get_authorized_client(
            membership_id=principal.membership_id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _require_open(self, review: ReconciliationReviewRecord) -> None:
        if review.status == ReconciliationReviewStatus.DISPUTED.value:
            raise ApiError(
                status_code=409,
                code="reconciliation_disputed",
                message="The disputed reconciliation review must be reopened before this action.",
            )
        if review.status != ReconciliationReviewStatus.OPEN.value:
            self._raise_terminal_or_invalid(review)

    def _require_nonterminal(self, review: ReconciliationReviewRecord) -> None:
        if ReconciliationReviewStatus(review.status) in TERMINAL_RECONCILIATION_REVIEW_STATUSES:
            raise ApiError(
                status_code=409,
                code="reconciliation_review_terminal",
                message="The reconciliation review is terminal and cannot be changed.",
            )

    def _raise_terminal_or_invalid(self, review: ReconciliationReviewRecord) -> None:
        self._require_nonterminal(review)
        raise ApiError(
            status_code=409,
            code="invalid_reconciliation_review_state",
            message="The reconciliation review cannot perform this action from its current state.",
        )

    def _add_action(
        self,
        *,
        principal: Principal,
        review: ReconciliationReviewRecord,
        action_type: ReconciliationReviewActionType,
        candidate_review_outcome_id: UUID | None,
        reason: str | None,
        request_id: str | None,
    ) -> None:
        self._reviews.add_action(
            ReconciliationReviewActionRecord(
                id=uuid.uuid4(),
                reconciliation_review_id=review.id,
                bank_transaction_id=review.bank_transaction_id,
                firm_id=review.firm_id,
                client_id=review.client_id,
                match_run_id=review.match_run_id,
                actor_user_id=principal.user_id,
                actor_membership_id=principal.membership_id,
                action_type=action_type.value,
                candidate_review_outcome_id=candidate_review_outcome_id,
                reason=reason,
                request_id=request_id,
            )
        )

    def _record_event(
        self,
        *,
        event_type: AuditEventType,
        principal: Principal,
        review: ReconciliationReviewRecord,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit.record_event(
            firm_id=review.firm_id,
            client_id=review.client_id,
            actor_user_id=principal.user_id,
            event_type=event_type.value,
            target_type="reconciliation_review",
            target_id=str(review.id),
            request_id=request_id,
            metadata={
                "bank_transaction_id": str(review.bank_transaction_id),
                "match_run_id": str(review.match_run_id),
                "status": review.status,
                **metadata,
            },
        )

    def _commit_or_raise(
        self,
        *,
        conflict_code: str = "reconciliation_persistence_conflict",
        conflict_message: str = "The reconciliation review conflicts with existing state.",
    ) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ApiError(
                status_code=409,
                code=conflict_code,
                message=conflict_message,
            ) from exc
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise ApiError(
                status_code=503,
                code="reconciliation_persistence_failed",
                message="Reconciliation review evidence could not be persisted.",
            ) from exc

    @staticmethod
    def _require_reason(reason: str, *, code: str) -> str:
        normalized = reason.strip()
        if not normalized:
            raise ApiError(
                status_code=422,
                code=code,
                message="A non-empty reason is required.",
            )
        return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _uuid_text(value: UUID | None) -> str | None:
    return str(value) if value is not None else None
