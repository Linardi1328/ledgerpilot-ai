from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.audit import AuditEvent
from ledgerpilot.persistence.models.review import ReviewComment, ReviewOutcome, ReviewTask
from ledgerpilot.persistence.repositories.audit import AuditRepository
from ledgerpilot.review.support import ReviewServiceSupport


class ReviewHistoryService(ReviewServiceSupport):
    def __init__(self, *, session: Session) -> None:
        super().__init__(session=session)
        self._audit_repository = AuditRepository(session)

    def get_history(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> tuple[ReviewTask, list[ReviewComment], ReviewOutcome | None, list[AuditEvent]]:
        self._require_history_reader_role(principal)
        self._require_client_access(principal=principal, client_id=client_id)
        task = self._get_task(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
        )
        comments = self._reviews.list_comments_for_task(
            firm_id=task.firm_id,
            client_id=task.client_id,
            decision_run_id=task.decision_run_id,
            review_task_id=task.id,
        )
        outcome = self._reviews.get_outcome_for_task(
            firm_id=task.firm_id,
            client_id=task.client_id,
            decision_run_id=task.decision_run_id,
            review_task_id=task.id,
        )
        audit_events = self._audit_repository.list_for_target(
            firm_id=task.firm_id,
            client_id=task.client_id,
            target_type="review_task",
            target_id=str(task.id),
        )
        return task, comments, outcome, audit_events
