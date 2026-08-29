from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ledgerpilot.accounting.states import AccountingDecisionRunStatus
from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.review import ReviewOutcome, ReviewTask
from ledgerpilot.persistence.repositories.accounting import AccountingRepository
from ledgerpilot.persistence.repositories.extraction import ExtractionRepository
from ledgerpilot.review.policy import classify_review_risk
from ledgerpilot.review.states import (
    ReviewEscalationState,
    ReviewOutcomeType,
    ReviewRiskClass,
    ReviewTaskStatus,
    transition_review_task_status,
)
from ledgerpilot.review.support import ReviewServiceSupport


class ReviewOutcomeService(ReviewServiceSupport):
    def __init__(self, *, session: Session) -> None:
        super().__init__(session=session)
        self._accounting = AccountingRepository(session)
        self._extractions = ExtractionRepository(session)

    def approve(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
        note: str | None,
        request_id: str | None,
    ) -> tuple[ReviewTask, ReviewOutcome]:
        self._require_reviewer_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        task = self._lock_task(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
        )
        self._require_active_task(task)
        self._require_owner(principal=principal, task=task)
        if task.status == ReviewTaskStatus.INFORMATION_REQUESTED.value:
            raise ApiError(
                status_code=409,
                code="information_response_required",
                message="Outstanding information must be resolved before approval.",
            )
        if task.status not in {
            ReviewTaskStatus.OPEN.value,
            ReviewTaskStatus.ESCALATED.value,
        }:
            raise ApiError(
                status_code=409,
                code="invalid_review_task_state",
                message="Review task cannot be approved from its current state.",
            )
        if (
            self._reviews.get_outcome_for_task(
                firm_id=task.firm_id,
                client_id=task.client_id,
                decision_run_id=task.decision_run_id,
                review_task_id=task.id,
            )
            is not None
        ):
            raise ApiError(
                status_code=409,
                code="review_outcome_exists",
                message="Review task already has a terminal outcome.",
            )

        decision = self._accounting.get_run_for_extraction(
            firm_id=task.firm_id,
            client_id=task.client_id,
            document_id=task.document_id,
            extraction_run_id=task.extraction_run_id,
            decision_run_id=task.decision_run_id,
        )
        if decision is None or decision.status != AccountingDecisionRunStatus.SUCCEEDED.value:
            raise ApiError(
                status_code=409,
                code="decision_not_reviewable",
                message="Accounting decision is not ready for approval.",
            )
        findings = self._accounting.list_findings_for_run(
            firm_id=task.firm_id,
            client_id=task.client_id,
            document_id=task.document_id,
            extraction_run_id=task.extraction_run_id,
            decision_run_id=task.decision_run_id,
        )
        proposed_journal = self._accounting.get_proposed_journal_for_run(
            firm_id=task.firm_id,
            client_id=task.client_id,
            document_id=task.document_id,
            extraction_run_id=task.extraction_run_id,
            decision_run_id=task.decision_run_id,
        )
        recomputed_risk = classify_review_risk(
            findings=findings,
            proposed_journal=proposed_journal,
        )
        if recomputed_risk.value != task.risk_class:
            raise ApiError(
                status_code=409,
                code="review_risk_changed",
                message="Review risk classification no longer matches the source decision.",
            )
        if proposed_journal is None or not proposed_journal.is_balanced:
            raise ApiError(
                status_code=409,
                code="review_approval_blocked",
                message="A balanced proposed journal is required for approval.",
            )

        corrections = self._extractions.list_corrections_for_run(
            firm_id=task.firm_id,
            client_id=task.client_id,
            document_id=task.document_id,
            run_id=task.extraction_run_id,
        )
        if any(correction.created_at > decision.created_at for correction in corrections):
            raise ApiError(
                status_code=409,
                code="decision_stale_after_correction",
                message="A newer extraction correction requires a fresh accounting decision.",
            )

        risk_class = ReviewRiskClass(task.risk_class)
        if Permission.APPROVE_ORDINARY_TRANSACTION not in principal.permissions:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")
        if risk_class == ReviewRiskClass.BLOCKED:
            raise ApiError(
                status_code=409,
                code="review_approval_blocked",
                message="Deterministic controls block approval for this accounting decision.",
            )
        if risk_class == ReviewRiskClass.SENIOR_REVIEW_REQUIRED:
            if (
                Permission.APPROVE_HIGH_RISK_TRANSACTION not in principal.permissions
                or principal.role != Role.SENIOR_REVIEWER
                or task.status != ReviewTaskStatus.ESCALATED.value
                or task.escalation_state != ReviewEscalationState.SENIOR_REVIEW.value
            ):
                raise ApiError(
                    status_code=403,
                    code="senior_review_required",
                    message="This review requires approval by the assigned senior reviewer.",
                )

        outcome_type = (
            ReviewOutcomeType.CORRECTED_AND_APPROVED if corrections else ReviewOutcomeType.APPROVED
        )
        outcome = ReviewOutcome(
            id=uuid.uuid4(),
            review_task_id=task.id,
            firm_id=task.firm_id,
            client_id=task.client_id,
            decision_run_id=task.decision_run_id,
            document_id=task.document_id,
            extraction_run_id=task.extraction_run_id,
            actor_user_id=principal.user_id,
            actor_membership_id=principal.membership_id,
            outcome_type=outcome_type.value,
            proposed_journal_id=proposed_journal.id,
            source_correction_count=len(corrections),
            reason=note.strip() if note is not None and note.strip() else None,
            request_id=request_id,
        )
        self._reviews.add_outcome(outcome)
        task.status = transition_review_task_status(
            ReviewTaskStatus(task.status),
            ReviewTaskStatus.APPROVED,
        ).value
        task.updated_at = datetime.now(UTC)
        self._record_event(
            event_type=AuditEventType.REVIEW_TASK_APPROVED,
            principal=principal,
            task=task,
            request_id=request_id,
            metadata={
                "outcome_id": str(outcome.id),
                "outcome_type": outcome.outcome_type,
                "decision_run_id": str(task.decision_run_id),
                "proposed_journal_id": str(proposed_journal.id),
                "source_correction_count": len(corrections),
                "risk_class": task.risk_class,
            },
        )
        self._commit_or_raise(task=task, request_id=request_id)
        return task, outcome

    def reject(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
        reason: str,
        request_id: str | None,
    ) -> tuple[ReviewTask, ReviewOutcome]:
        self._require_reviewer_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        task = self._lock_task(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
        )
        self._require_active_task(task)
        self._require_owner(principal=principal, task=task)
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ApiError(
                status_code=422,
                code="rejection_reason_required",
                message="A rejection reason is required.",
            )
        if (
            self._reviews.get_outcome_for_task(
                firm_id=task.firm_id,
                client_id=task.client_id,
                decision_run_id=task.decision_run_id,
                review_task_id=task.id,
            )
            is not None
        ):
            raise ApiError(
                status_code=409,
                code="review_outcome_exists",
                message="Review task already has a terminal outcome.",
            )

        current_status = ReviewTaskStatus(task.status)
        outcome = ReviewOutcome(
            id=uuid.uuid4(),
            review_task_id=task.id,
            firm_id=task.firm_id,
            client_id=task.client_id,
            decision_run_id=task.decision_run_id,
            document_id=task.document_id,
            extraction_run_id=task.extraction_run_id,
            actor_user_id=principal.user_id,
            actor_membership_id=principal.membership_id,
            outcome_type=ReviewOutcomeType.REJECTED.value,
            proposed_journal_id=None,
            source_correction_count=0,
            reason=normalized_reason,
            request_id=request_id,
        )
        self._reviews.add_outcome(outcome)
        task.status = transition_review_task_status(
            current_status,
            ReviewTaskStatus.REJECTED,
        ).value
        task.updated_at = datetime.now(UTC)
        self._record_event(
            event_type=AuditEventType.REVIEW_TASK_REJECTED,
            principal=principal,
            task=task,
            request_id=request_id,
            metadata={
                "outcome_id": str(outcome.id),
                "outcome_type": outcome.outcome_type,
                "decision_run_id": str(task.decision_run_id),
                "risk_class": task.risk_class,
            },
        )
        self._commit_or_raise(task=task, request_id=request_id)
        return task, outcome
