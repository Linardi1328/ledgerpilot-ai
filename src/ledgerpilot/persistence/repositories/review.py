from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.review import ReviewTask


class ReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, task: ReviewTask) -> ReviewTask:
        self._session.add(task)
        return task

    def get_for_decision(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> ReviewTask | None:
        statement = select(ReviewTask).where(
            ReviewTask.id == review_task_id,
            ReviewTask.firm_id == firm_id,
            ReviewTask.client_id == client_id,
            ReviewTask.document_id == document_id,
            ReviewTask.extraction_run_id == extraction_run_id,
            ReviewTask.decision_run_id == decision_run_id,
        )
        return self._session.scalar(statement)

    def get_by_decision(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> ReviewTask | None:
        statement = select(ReviewTask).where(
            ReviewTask.firm_id == firm_id,
            ReviewTask.client_id == client_id,
            ReviewTask.document_id == document_id,
            ReviewTask.extraction_run_id == extraction_run_id,
            ReviewTask.decision_run_id == decision_run_id,
        )
        return self._session.scalar(statement)

    def list_for_decision(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> list[ReviewTask]:
        statement = (
            select(ReviewTask)
            .where(
                ReviewTask.firm_id == firm_id,
                ReviewTask.client_id == client_id,
                ReviewTask.document_id == document_id,
                ReviewTask.extraction_run_id == extraction_run_id,
                ReviewTask.decision_run_id == decision_run_id,
            )
            .order_by(ReviewTask.created_at.asc())
        )
        return list(self._session.scalars(statement))
