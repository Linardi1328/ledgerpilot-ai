from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ledgerpilot.api.errors import ApiError
from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.reconciliation import (
    BankTransactionRecord,
    ReconciliationMatchRunRecord,
)
from ledgerpilot.persistence.models.reconciliation_review import (
    ReconciliationOutcomeRecord,
    ReconciliationReviewRecord,
)
from ledgerpilot.persistence.repositories.clients import ClientRepository
from ledgerpilot.persistence.repositories.reconciliation_worklist import (
    ReconciliationWorklistRepository,
)
from ledgerpilot.reconciliation.states import (
    ReconciliationReviewStatus,
    ReconciliationWorkflowState,
)
from ledgerpilot.reconciliation.types import ReconciliationCandidateStatus


@dataclass(frozen=True)
class ReconciliationWorklistItem:
    transaction: BankTransactionRecord
    workflow_state: ReconciliationWorkflowState
    latest_match_run: ReconciliationMatchRunRecord | None
    review: ReconciliationReviewRecord | None
    outcome: ReconciliationOutcomeRecord | None
    last_activity_at: datetime


class ReconciliationWorklistService:
    def __init__(self, *, session: Session) -> None:
        self._clients = ClientRepository(session)
        self._worklist = ReconciliationWorklistRepository(session)

    def list_items(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        state: ReconciliationWorkflowState | None,
        limit: int,
    ) -> tuple[ReconciliationWorklistItem, ...]:
        self._require_client_access(principal=principal, client_id=client_id)
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")

        latest_runs: dict[UUID, ReconciliationMatchRunRecord] = {}
        for run in self._worklist.list_match_runs(
            firm_id=principal.firm_id,
            client_id=client_id,
        ):
            latest_runs[run.bank_transaction_id] = run

        reviews = {
            review.bank_transaction_id: review
            for review in self._worklist.list_reviews(
                firm_id=principal.firm_id,
                client_id=client_id,
            )
        }
        outcomes = {
            outcome.bank_transaction_id: outcome
            for outcome in self._worklist.list_outcomes(
                firm_id=principal.firm_id,
                client_id=client_id,
            )
        }

        items: list[ReconciliationWorklistItem] = []
        for transaction in self._worklist.list_transactions(
            firm_id=principal.firm_id,
            client_id=client_id,
        ):
            run = latest_runs.get(transaction.id)
            review = reviews.get(transaction.id)
            outcome = outcomes.get(transaction.id)
            workflow_state = _project_workflow_state(run=run, review=review)
            if state is not None and workflow_state is not state:
                continue
            items.append(
                ReconciliationWorklistItem(
                    transaction=transaction,
                    workflow_state=workflow_state,
                    latest_match_run=run,
                    review=review,
                    outcome=outcome,
                    last_activity_at=_last_activity_at(
                        transaction=transaction,
                        run=run,
                        review=review,
                        outcome=outcome,
                    ),
                )
            )
            if len(items) >= limit:
                break
        return tuple(items)

    def _require_client_access(self, *, principal: Principal, client_id: UUID) -> None:
        client = self._clients.get_authorized_client(
            membership_id=principal.membership_id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")


def _project_workflow_state(
    *,
    run: ReconciliationMatchRunRecord | None,
    review: ReconciliationReviewRecord | None,
) -> ReconciliationWorkflowState:
    if review is not None:
        try:
            review_status = ReconciliationReviewStatus(review.status)
        except ValueError as exc:
            raise ApiError(
                status_code=503,
                code="reconciliation_state_invalid",
                message="Stored reconciliation review state is invalid.",
            ) from exc
        if review_status is ReconciliationReviewStatus.OPEN:
            return ReconciliationWorkflowState.IN_REVIEW
        if review_status is ReconciliationReviewStatus.DISPUTED:
            return ReconciliationWorkflowState.DISPUTED
        if review_status is ReconciliationReviewStatus.MATCHED:
            return ReconciliationWorkflowState.MATCHED
        return ReconciliationWorkflowState.RESOLVED_UNMATCHED

    if run is None:
        return ReconciliationWorkflowState.NOT_EVALUATED
    try:
        run_status = ReconciliationCandidateStatus(run.status)
    except ValueError as exc:
        raise ApiError(
            status_code=503,
            code="reconciliation_state_invalid",
            message="Stored reconciliation match state is invalid.",
        ) from exc
    if run_status is ReconciliationCandidateStatus.CANDIDATES_AVAILABLE:
        return ReconciliationWorkflowState.CANDIDATES_AVAILABLE
    return ReconciliationWorkflowState.UNMATCHED


def _last_activity_at(
    *,
    transaction: BankTransactionRecord,
    run: ReconciliationMatchRunRecord | None,
    review: ReconciliationReviewRecord | None,
    outcome: ReconciliationOutcomeRecord | None,
) -> datetime:
    latest = transaction.created_at
    for timestamp in (
        run.created_at if run is not None else None,
        review.updated_at if review is not None else None,
        outcome.created_at if outcome is not None else None,
    ):
        if timestamp is not None and timestamp > latest:
            latest = timestamp
    return latest
