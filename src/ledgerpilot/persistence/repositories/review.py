from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.review import ReviewComment, ReviewOutcome, ReviewTask
from ledgerpilot.review.states import ReviewOutcomeType


class ReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, task: ReviewTask) -> ReviewTask:
        self._session.add(task)
        return task

    def add_comment(self, comment: ReviewComment) -> ReviewComment:
        self._session.add(comment)
        return comment

    def add_outcome(self, outcome: ReviewOutcome) -> ReviewOutcome:
        self._session.add(outcome)
        return outcome

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

    def lock_for_decision(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> ReviewTask | None:
        statement = (
            select(ReviewTask)
            .where(
                ReviewTask.id == review_task_id,
                ReviewTask.firm_id == firm_id,
                ReviewTask.client_id == client_id,
                ReviewTask.document_id == document_id,
                ReviewTask.extraction_run_id == extraction_run_id,
                ReviewTask.decision_run_id == decision_run_id,
            )
            .with_for_update()
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

    def list_comments_for_task(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> list[ReviewComment]:
        statement = (
            select(ReviewComment)
            .where(
                ReviewComment.review_task_id == review_task_id,
                ReviewComment.firm_id == firm_id,
                ReviewComment.client_id == client_id,
                ReviewComment.decision_run_id == decision_run_id,
            )
            .order_by(ReviewComment.created_at.asc(), ReviewComment.id.asc())
        )
        return list(self._session.scalars(statement))

    def get_outcome_for_task(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        decision_run_id: UUID,
        review_task_id: UUID,
    ) -> ReviewOutcome | None:
        statement = select(ReviewOutcome).where(
            ReviewOutcome.review_task_id == review_task_id,
            ReviewOutcome.firm_id == firm_id,
            ReviewOutcome.client_id == client_id,
            ReviewOutcome.decision_run_id == decision_run_id,
        )
        return self._session.scalar(statement)

    def has_approved_outcome_for_extraction(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
    ) -> bool:
        statement = select(ReviewOutcome.id).where(
            ReviewOutcome.firm_id == firm_id,
            ReviewOutcome.client_id == client_id,
            ReviewOutcome.document_id == document_id,
            ReviewOutcome.extraction_run_id == extraction_run_id,
            ReviewOutcome.outcome_type.in_(
                (
                    ReviewOutcomeType.APPROVED.value,
                    ReviewOutcomeType.CORRECTED_AND_APPROVED.value,
                )
            ),
        )
        return self._session.scalar(statement) is not None
