from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import NoReturn
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.accounting.states import AccountingDecisionRunStatus
from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.service import AuditService
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.accounting import AccountingDecisionRun
from ledgerpilot.persistence.models.identity import FirmMembership
from ledgerpilot.persistence.models.review import ReviewTask
from ledgerpilot.persistence.repositories.accounting import AccountingRepository
from ledgerpilot.persistence.repositories.clients import ClientRepository
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from ledgerpilot.persistence.repositories.review import ReviewRepository
from ledgerpilot.review.states import (
    ReviewEscalationState,
    ReviewTaskStatus,
    transition_review_task_status,
)

logger = logging.getLogger(__name__)

_REVIEWER_ROLES = frozenset({Role.ACCOUNTANT, Role.SENIOR_REVIEWER})
_REVIEWER_ROLE_VALUES = frozenset(role.value for role in _REVIEWER_ROLES)


class ReviewTaskService:
    def __init__(self, *, session: Session) -> None:
        self._session = session
        self._accounting = AccountingRepository(session)
        self._clients = ClientRepository(session)
        self._identity = IdentityRepository(session)
        self._reviews = ReviewRepository(session)
        self._audit = AuditService(session)

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
            raise ApiError(
                status_code=409,
                code="review_task_exists",
                message="A review task already exists for this accounting decision.",
            )

        owner = self._resolve_owner(
            principal=principal,
            client_id=client_id,
            owner_membership_id=owner_membership_id or principal.membership_id,
            require_senior=False,
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
                "escalation_state": task.escalation_state,
            },
        )
        self._commit_or_raise(task=task, request_id=request_id)
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
        self._require_reviewer_role(principal)
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
        self._require_reviewer_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        task = self._reviews.get_for_decision(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
        )
        if task is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return task

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
    ) -> ReviewTask:
        self._require_reviewer_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        task = self.get_task(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
        )
        if task.escalation_state != ReviewEscalationState.NONE.value:
            raise ApiError(
                status_code=409,
                code="review_task_already_escalated",
                message="Review task has already been escalated.",
            )
        senior = self._resolve_owner(
            principal=principal,
            client_id=client_id,
            owner_membership_id=senior_membership_id,
            require_senior=True,
        )

        current_status = ReviewTaskStatus(task.status)
        try:
            task.status = transition_review_task_status(
                current_status,
                ReviewTaskStatus.ESCALATED,
            ).value
        except ValueError as exc:
            raise ApiError(
                status_code=409,
                code="invalid_review_task_state",
                message="Review task cannot be escalated from its current state.",
            ) from exc

        previous_owner_membership_id = task.owner_membership_id
        now = datetime.now(UTC)
        task.owner_user_id = senior.user_id
        task.owner_membership_id = senior.id
        task.escalation_state = ReviewEscalationState.SENIOR_REVIEW.value
        task.escalated_at = now
        task.updated_at = now
        self._record_event(
            event_type=AuditEventType.REVIEW_TASK_ESCALATED,
            principal=principal,
            task=task,
            request_id=request_id,
            metadata={
                "decision_run_id": str(task.decision_run_id),
                "previous_owner_membership_id": str(previous_owner_membership_id),
                "senior_owner_membership_id": str(task.owner_membership_id),
                "status": task.status,
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

    def _resolve_owner(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        owner_membership_id: UUID,
        require_senior: bool,
    ) -> FirmMembership:
        membership = self._identity.get_active_membership_by_id_for_firm(
            membership_id=owner_membership_id,
            firm_id=principal.firm_id,
        )
        if membership is None:
            self._raise_invalid_owner()
        if require_senior:
            if membership.role != Role.SENIOR_REVIEWER.value:
                self._raise_invalid_owner()
        elif membership.role not in _REVIEWER_ROLE_VALUES:
            self._raise_invalid_owner()

        client = self._clients.get_authorized_client(
            membership_id=membership.id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            self._raise_invalid_owner()
        return membership

    def _require_reviewer_role(self, principal: Principal) -> None:
        if principal.role not in _REVIEWER_ROLES:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _require_client_access(self, *, principal: Principal, client_id: UUID) -> None:
        client = self._clients.get_authorized_client(
            membership_id=principal.membership_id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _record_event(
        self,
        *,
        event_type: AuditEventType,
        principal: Principal,
        task: ReviewTask,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit.record_event(
            firm_id=task.firm_id,
            client_id=task.client_id,
            actor_user_id=principal.user_id,
            event_type=event_type.value,
            target_type="review_task",
            target_id=str(task.id),
            request_id=request_id,
            metadata=metadata,
        )

    def _commit_or_raise(self, *, task: ReviewTask, request_id: str | None) -> None:
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            logger.warning(
                "Review task persistence failed",
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

    def _raise_invalid_owner(self) -> NoReturn:
        raise ApiError(
            status_code=422,
            code="invalid_review_owner",
            message="Review owner must be an active accountant or senior reviewer for this client.",
        )
