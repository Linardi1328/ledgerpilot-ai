from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import NoReturn
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.accounting.states import AccountingDecisionRunStatus
from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.accounting import AccountingDecisionRun
from ledgerpilot.persistence.models.review import ReviewTask
from ledgerpilot.persistence.repositories.accounting import AccountingRepository
from ledgerpilot.review.policy import classify_review_risk
from ledgerpilot.review.states import (
    ReviewCommentKind,
    ReviewEscalationState,
    ReviewTaskStatus,
    transition_review_task_status,
)
from ledgerpilot.review.support import ReviewServiceSupport

logger = logging.getLogger(__name__)


class ReviewTaskService(ReviewServiceSupport):
    def __init__(self, *, session: Session) -> None:
        super().__init__(session=session)
        self._accounting = AccountingRepository(session)

    def create_task(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        owner_membership_id: UUID | None,
        request_id: str | None,
    ) -> ReviewTask:
        self._require_reviewer_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        decision = self._get_reviewable_decision_or_error(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
        )
        if (
            self._reviews.get_by_decision(
                firm_id=principal.firm_id,
                client_id=client_id,
                document_id=document_id,
                extraction_run_id=extraction_run_id,
                decision_run_id=decision_run_id,
            )
            is not None
        ):
            self._raise_duplicate_task()

        owner = self._resolve_owner(
            principal=principal,
            client_id=client_id,
            owner_membership_id=owner_membership_id or principal.membership_id,
            require_senior=False,
        )
        findings = self._accounting.list_findings_for_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
        )
        proposed_journal = self._accounting.get_proposed_journal_for_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
        )
        risk_class = classify_review_risk(
            findings=findings,
            proposed_journal=proposed_journal,
        )
        task = ReviewTask(
            id=uuid.uuid4(),
            firm_id=decision.firm_id,
            client_id=decision.client_id,
            decision_run_id=decision.id,
            document_id=decision.document_id,
            extraction_run_id=decision.extraction_run_id,
            created_by_user_id=principal.user_id,
            created_by_membership_id=principal.membership_id,
            owner_user_id=owner.user_id,
            owner_membership_id=owner.id,
            status=ReviewTaskStatus.OPEN.value,
            risk_class=risk_class.value,
            escalation_state=ReviewEscalationState.NONE.value,
            request_id=request_id,
        )
        self._reviews.add(task)
        self._record_event(
            event_type=AuditEventType.REVIEW_TASK_CREATED,
            principal=principal,
            task=task,
            request_id=request_id,
            metadata={
                "decision_run_id": str(task.decision_run_id),
                "owner_membership_id": str(task.owner_membership_id),
                "status": task.status,
                "risk_class": task.risk_class,
                "escalation_state": task.escalation_state,
            },
        )
        self._commit_creation_or_raise(task=task, request_id=request_id)
        return task

    def list_tasks(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> list[ReviewTask]:
        self._require_history_reader_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        self._get_reviewable_decision_or_error(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
        )
        return self._reviews.list_for_decision(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
        )

    def get_task(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> ReviewTask:
        self._require_history_reader_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        return self._get_task(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
        )

    def escalate_to_senior(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
        senior_membership_id: UUID,
        request_id: str | None,
        reason: str = "Senior review escalation.",
    ) -> ReviewTask:
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
        if task.status != ReviewTaskStatus.OPEN.value:
            raise ApiError(
                status_code=409,
                code="invalid_review_task_state",
                message="Only an open review task can be escalated.",
            )

        senior = self._resolve_owner(
            principal=principal,
            client_id=client_id,
            owner_membership_id=senior_membership_id,
            require_senior=True,
        )
        previous_owner_membership_id = task.owner_membership_id
        task.status = transition_review_task_status(
            ReviewTaskStatus(task.status),
            ReviewTaskStatus.ESCALATED,
        ).value
        now = datetime.now(UTC)
        task.owner_user_id = senior.user_id
        task.owner_membership_id = senior.id
        task.escalation_state = ReviewEscalationState.SENIOR_REVIEW.value
        task.escalated_at = now
        task.updated_at = now
        comment = self._new_comment(
            principal=principal,
            task=task,
            kind=ReviewCommentKind.ESCALATION_REASON,
            body=reason,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.REVIEW_TASK_ESCALATED,
            principal=principal,
            task=task,
            request_id=request_id,
            metadata={
                "decision_run_id": str(task.decision_run_id),
                "previous_owner_membership_id": str(previous_owner_membership_id),
                "senior_owner_membership_id": str(task.owner_membership_id),
                "reason_comment_id": str(comment.id),
                "status": task.status,
                "risk_class": task.risk_class,
                "escalation_state": task.escalation_state,
            },
        )
        self._commit_or_raise(task=task, request_id=request_id)
        return task

    def _get_reviewable_decision_or_error(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> AccountingDecisionRun:
        decision = self._accounting.get_run_for_extraction(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
        )
        if decision is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        if decision.status != AccountingDecisionRunStatus.SUCCEEDED.value:
            raise ApiError(
                status_code=409,
                code="decision_not_reviewable",
                message="Accounting decision is not ready for human review.",
            )
        return decision

    def _commit_creation_or_raise(
        self,
        *,
        task: ReviewTask,
        request_id: str | None,
    ) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            existing = self._reviews.get_by_decision(
                firm_id=task.firm_id,
                client_id=task.client_id,
                document_id=task.document_id,
                extraction_run_id=task.extraction_run_id,
                decision_run_id=task.decision_run_id,
            )
            if existing is not None:
                self._raise_duplicate_task()
            self._raise_creation_persistence_error(task=task, request_id=request_id, exc=exc)
        except SQLAlchemyError as exc:
            self._session.rollback()
            self._raise_creation_persistence_error(task=task, request_id=request_id, exc=exc)

    def _raise_creation_persistence_error(
        self,
        *,
        task: ReviewTask,
        request_id: str | None,
        exc: SQLAlchemyError,
    ) -> NoReturn:
        logger.warning(
            "Review task creation persistence failed",
            extra={
                "request_id": request_id,
                "review_task_id": str(task.id),
                "exception_type": type(exc).__name__,
            },
        )
        raise ApiError(
            status_code=503,
            code="review_persistence_failed",
            message="Review task state could not be persisted.",
        ) from exc

    def _raise_duplicate_task(self) -> NoReturn:
        raise ApiError(
            status_code=409,
            code="review_task_exists",
            message="A review task already exists for this accounting decision.",
        )
