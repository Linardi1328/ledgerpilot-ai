from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.reconciliation import (
    BankTransactionRecord,
    ReconciliationCandidateRecord,
    ReconciliationMatchRunRecord,
)
from ledgerpilot.persistence.models.reconciliation_review import (
    ReconciliationOutcomeRecord,
    ReconciliationReviewActionRecord,
    ReconciliationReviewRecord,
)


class ReconciliationReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_transaction(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        bank_transaction_id: UUID,
    ) -> BankTransactionRecord | None:
        statement = (
            select(BankTransactionRecord)
            .where(
                BankTransactionRecord.id == bank_transaction_id,
                BankTransactionRecord.firm_id == firm_id,
                BankTransactionRecord.client_id == client_id,
            )
            .with_for_update()
        )
        return self._session.scalar(statement)

    def get_match_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        bank_transaction_id: UUID,
        match_run_id: UUID,
    ) -> ReconciliationMatchRunRecord | None:
        statement = select(ReconciliationMatchRunRecord).where(
            ReconciliationMatchRunRecord.id == match_run_id,
            ReconciliationMatchRunRecord.bank_transaction_id == bank_transaction_id,
            ReconciliationMatchRunRecord.firm_id == firm_id,
            ReconciliationMatchRunRecord.client_id == client_id,
        )
        return self._session.scalar(statement)

    def get_candidate_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        bank_transaction_id: UUID,
        match_run_id: UUID,
        review_outcome_id: UUID,
    ) -> ReconciliationCandidateRecord | None:
        statement = select(ReconciliationCandidateRecord).where(
            ReconciliationCandidateRecord.match_run_id == match_run_id,
            ReconciliationCandidateRecord.bank_transaction_id == bank_transaction_id,
            ReconciliationCandidateRecord.firm_id == firm_id,
            ReconciliationCandidateRecord.client_id == client_id,
            ReconciliationCandidateRecord.review_outcome_id == review_outcome_id,
        )
        return self._session.scalar(statement)

    def add_review(self, review: ReconciliationReviewRecord) -> ReconciliationReviewRecord:
        self._session.add(review)
        return review

    def get_review_for_transaction(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        bank_transaction_id: UUID,
    ) -> ReconciliationReviewRecord | None:
        statement = select(ReconciliationReviewRecord).where(
            ReconciliationReviewRecord.bank_transaction_id == bank_transaction_id,
            ReconciliationReviewRecord.firm_id == firm_id,
            ReconciliationReviewRecord.client_id == client_id,
        )
        return self._session.scalar(statement)

    def lock_review(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        bank_transaction_id: UUID,
        reconciliation_review_id: UUID,
    ) -> ReconciliationReviewRecord | None:
        statement = (
            select(ReconciliationReviewRecord)
            .where(
                ReconciliationReviewRecord.id == reconciliation_review_id,
                ReconciliationReviewRecord.bank_transaction_id == bank_transaction_id,
                ReconciliationReviewRecord.firm_id == firm_id,
                ReconciliationReviewRecord.client_id == client_id,
            )
            .with_for_update()
        )
        return self._session.scalar(statement)

    def add_action(
        self,
        action: ReconciliationReviewActionRecord,
    ) -> ReconciliationReviewActionRecord:
        self._session.add(action)
        return action

    def list_actions(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        reconciliation_review_id: UUID,
    ) -> list[ReconciliationReviewActionRecord]:
        statement = (
            select(ReconciliationReviewActionRecord)
            .where(
                ReconciliationReviewActionRecord.reconciliation_review_id
                == reconciliation_review_id,
                ReconciliationReviewActionRecord.firm_id == firm_id,
                ReconciliationReviewActionRecord.client_id == client_id,
            )
            .order_by(
                ReconciliationReviewActionRecord.created_at.asc(),
                ReconciliationReviewActionRecord.id.asc(),
            )
        )
        return list(self._session.scalars(statement))

    def add_outcome(
        self,
        outcome: ReconciliationOutcomeRecord,
    ) -> ReconciliationOutcomeRecord:
        self._session.add(outcome)
        return outcome

    def get_outcome_for_review(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        reconciliation_review_id: UUID,
    ) -> ReconciliationOutcomeRecord | None:
        statement = select(ReconciliationOutcomeRecord).where(
            ReconciliationOutcomeRecord.reconciliation_review_id == reconciliation_review_id,
            ReconciliationOutcomeRecord.firm_id == firm_id,
            ReconciliationOutcomeRecord.client_id == client_id,
        )
        return self._session.scalar(statement)

    def get_matched_outcome_for_review_outcome(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        review_outcome_id: UUID,
    ) -> ReconciliationOutcomeRecord | None:
        statement = select(ReconciliationOutcomeRecord).where(
            ReconciliationOutcomeRecord.firm_id == firm_id,
            ReconciliationOutcomeRecord.client_id == client_id,
            ReconciliationOutcomeRecord.matched_review_outcome_id == review_outcome_id,
        )
        return self._session.scalar(statement)
