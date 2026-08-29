from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.review import ReviewComment, ReviewTask
from ledgerpilot.review.states import (
    ReviewCommentKind,
    ReviewEscalationState,
    ReviewTaskStatus,
    transition_review_task_status,
)
from ledgerpilot.review.support import ReviewServiceSupport


class ReviewInteractionService(ReviewServiceSupport):
    def __init__(self, *, session: Session) -> None:
        super().__init__(session=session)

    def add_comment(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
        body: str,
        request_id: str | None,
    ) -> ReviewComment:
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
        comment = self._new_comment(
            principal=principal,
            task=task,
            kind=ReviewCommentKind.COMMENT,
            body=body,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.REVIEW_COMMENT_ADDED,
            principal=principal,
            task=task,
            request_id=request_id,
            metadata={
                "comment_id": str(comment.id),
                "comment_kind": comment.kind,
            },
        )
        self._commit_or_raise(task=task, request_id=request_id)
        return comment

    def request_information(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
        body: str,
        request_id: str | None,
    ) -> tuple[ReviewTask, ReviewComment]:
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
        if task.status not in {
            ReviewTaskStatus.OPEN.value,
            ReviewTaskStatus.ESCALATED.value,
        }:
            raise ApiError(
                status_code=409,
                code="invalid_review_task_state",
                message="Information can only be requested from an active review state.",
            )

        task.status = transition_review_task_status(
            ReviewTaskStatus(task.status),
            ReviewTaskStatus.INFORMATION_REQUESTED,
        ).value
        task.updated_at = datetime.now(UTC)
        comment = self._new_comment(
            principal=principal,
            task=task,
            kind=ReviewCommentKind.INFORMATION_REQUEST,
            body=body,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.REVIEW_INFORMATION_REQUESTED,
            principal=principal,
            task=task,
            request_id=request_id,
            metadata={
                "comment_id": str(comment.id),
                "status": task.status,
                "escalation_state": task.escalation_state,
            },
        )
        self._commit_or_raise(task=task, request_id=request_id)
        return task, comment

    def get_information_request(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> ReviewComment:
        self._require_client_submitter_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        task = self._get_task(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
        )
        if task.status != ReviewTaskStatus.INFORMATION_REQUESTED.value:
            raise ApiError(
                status_code=409,
                code="information_not_requested",
                message="This review task is not waiting for information.",
            )
        comments = self._reviews.list_comments_for_task(
            firm_id=task.firm_id,
            client_id=task.client_id,
            decision_run_id=task.decision_run_id,
            review_task_id=task.id,
        )
        for comment in reversed(comments):
            if comment.kind == ReviewCommentKind.INFORMATION_REQUEST.value:
                return comment
        raise ApiError(
            status_code=409,
            code="information_request_missing",
            message="The outstanding information request could not be found.",
        )

    def respond_to_information_request(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
        body: str,
        request_id: str | None,
    ) -> tuple[ReviewTask, ReviewComment]:
        self._require_client_submitter_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        task = self._lock_task(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
        )
        if task.status != ReviewTaskStatus.INFORMATION_REQUESTED.value:
            raise ApiError(
                status_code=409,
                code="information_not_requested",
                message="This review task is not waiting for information.",
            )

        resume_status = (
            ReviewTaskStatus.ESCALATED
            if task.escalation_state == ReviewEscalationState.SENIOR_REVIEW.value
            else ReviewTaskStatus.OPEN
        )
        task.status = transition_review_task_status(
            ReviewTaskStatus.INFORMATION_REQUESTED,
            resume_status,
        ).value
        task.updated_at = datetime.now(UTC)
        comment = self._new_comment(
            principal=principal,
            task=task,
            kind=ReviewCommentKind.INFORMATION_RESPONSE,
            body=body,
            request_id=request_id,
        )
        self._record_event(
            event_type=AuditEventType.REVIEW_INFORMATION_RESPONDED,
            principal=principal,
            task=task,
            request_id=request_id,
            metadata={
                "comment_id": str(comment.id),
                "status": task.status,
                "escalation_state": task.escalation_state,
            },
        )
        self._commit_or_raise(task=task, request_id=request_id)
        return task, comment
