from __future__ import annotations

import logging
import uuid
from typing import NoReturn
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.service import AuditService
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.identity import FirmMembership
from ledgerpilot.persistence.models.review import ReviewComment, ReviewTask
from ledgerpilot.persistence.repositories.clients import ClientRepository
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from ledgerpilot.persistence.repositories.review import ReviewRepository
from ledgerpilot.review.states import ReviewCommentKind, ReviewTaskStatus, is_terminal_review_status

logger = logging.getLogger(__name__)

REVIEWER_ROLES = frozenset({Role.ACCOUNTANT, Role.SENIOR_REVIEWER})
REVIEWER_ROLE_VALUES = frozenset(role.value for role in REVIEWER_ROLES)
HISTORY_READER_ROLES = frozenset({Role.ACCOUNTANT, Role.SENIOR_REVIEWER, Role.AUDITOR})


class ReviewServiceSupport:
    def __init__(self, *, session: Session) -> None:
        self._session = session
        self._clients = ClientRepository(session)
        self._identity = IdentityRepository(session)
        self._reviews = ReviewRepository(session)
        self._audit = AuditService(session)

    def _require_reviewer_role(self, principal: Principal) -> None:
        if principal.role not in REVIEWER_ROLES:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _require_history_reader_role(self, principal: Principal) -> None:
        if principal.role not in HISTORY_READER_ROLES:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _require_client_submitter_role(self, principal: Principal) -> None:
        if principal.role != Role.CLIENT_SUBMITTER:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _require_client_access(self, *, principal: Principal, client_id: UUID) -> None:
        client = self._clients.get_authorized_client(
            membership_id=principal.membership_id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _require_owner(self, *, principal: Principal, task: ReviewTask) -> None:
        if task.owner_membership_id != principal.membership_id:
            raise ApiError(
                status_code=403,
                code="review_task_not_owned",
                message="Review action requires current task ownership.",
            )

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
        elif membership.role not in REVIEWER_ROLE_VALUES:
            self._raise_invalid_owner()

        client = self._clients.get_authorized_client(
            membership_id=membership.id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            self._raise_invalid_owner()
        return membership

    def _get_task(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> ReviewTask:
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

    def _lock_task(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> ReviewTask:
        task = self._reviews.lock_for_decision(
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

    def _require_active_task(self, task: ReviewTask) -> None:
        status = ReviewTaskStatus(task.status)
        if is_terminal_review_status(status):
            raise ApiError(
                status_code=409,
                code="review_task_terminal",
                message="Review task is already resolved.",
            )

    def _new_comment(
        self,
        *,
        principal: Principal,
        task: ReviewTask,
        kind: ReviewCommentKind,
        body: str,
        request_id: str | None,
    ) -> ReviewComment:
        normalized_body = body.strip()
        if not normalized_body:
            raise ApiError(
                status_code=422,
                code="review_comment_required",
                message="Review comment text is required.",
            )
        comment = ReviewComment(
            id=uuid.uuid4(),
            review_task_id=task.id,
            firm_id=task.firm_id,
            client_id=task.client_id,
            decision_run_id=task.decision_run_id,
            author_user_id=principal.user_id,
            author_membership_id=principal.membership_id,
            kind=kind.value,
            body=normalized_body,
            request_id=request_id,
        )
        self._reviews.add_comment(comment)
        return comment

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

    def _commit_or_raise(
        self,
        *,
        task: ReviewTask,
        request_id: str | None,
        code: str = "review_persistence_failed",
    ) -> None:
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            logger.warning(
                "Review persistence failed",
                extra={
                    "request_id": request_id,
                    "review_task_id": str(task.id),
                    "exception_type": type(exc).__name__,
                },
            )
            raise ApiError(
                status_code=503,
                code=code,
                message="Review state could not be persisted.",
            ) from exc

    def _raise_invalid_owner(self) -> NoReturn:
        raise ApiError(
            status_code=422,
            code="invalid_review_owner",
            message="Review owner must be an active accountant or senior reviewer for this client.",
        )
