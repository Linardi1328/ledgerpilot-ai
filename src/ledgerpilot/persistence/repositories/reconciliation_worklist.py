from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.reconciliation import (
    BankTransactionRecord,
    ReconciliationMatchRunRecord,
)
from ledgerpilot.persistence.models.reconciliation_review import (
    ReconciliationOutcomeRecord,
    ReconciliationReviewRecord,
)


class ReconciliationWorklistRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_transactions(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
    ) -> list[BankTransactionRecord]:
        statement = (
            select(BankTransactionRecord)
            .where(
                BankTransactionRecord.firm_id == firm_id,
                BankTransactionRecord.client_id == client_id,
            )
            .order_by(
                BankTransactionRecord.booking_date.desc(),
                BankTransactionRecord.created_at.desc(),
                BankTransactionRecord.id.desc(),
            )
        )
        return list(self._session.scalars(statement))

    def list_match_runs(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
    ) -> list[ReconciliationMatchRunRecord]:
        statement = (
            select(ReconciliationMatchRunRecord)
            .where(
                ReconciliationMatchRunRecord.firm_id == firm_id,
                ReconciliationMatchRunRecord.client_id == client_id,
            )
            .order_by(
                ReconciliationMatchRunRecord.created_at.asc(),
                ReconciliationMatchRunRecord.id.asc(),
            )
        )
        return list(self._session.scalars(statement))

    def list_reviews(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
    ) -> list[ReconciliationReviewRecord]:
        statement = select(ReconciliationReviewRecord).where(
            ReconciliationReviewRecord.firm_id == firm_id,
            ReconciliationReviewRecord.client_id == client_id,
        )
        return list(self._session.scalars(statement))

    def list_outcomes(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
    ) -> list[ReconciliationOutcomeRecord]:
        statement = select(ReconciliationOutcomeRecord).where(
            ReconciliationOutcomeRecord.firm_id == firm_id,
            ReconciliationOutcomeRecord.client_id == client_id,
        )
        return list(self._session.scalars(statement))
