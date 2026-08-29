from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.reconciliation import (
    BankImportBatchRecord,
    BankTransactionRecord,
    ReconciliationCandidateRecord,
    ReconciliationMatchRunRecord,
)
from ledgerpilot.reconciliation.types import (
    BankImportBatch,
    ReconciliationMatchResult,
)


class ReconciliationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_import_batch(self, batch: BankImportBatch) -> BankImportBatchRecord:
        batch_id = uuid4()
        record = BankImportBatchRecord(
            id=batch_id,
            firm_id=batch.firm_id,
            client_id=batch.client_id,
            provider_name=batch.provider_name.strip(),
            provider_version=batch.provider_version.strip(),
            provider_batch_reference=batch.provider_batch_reference.strip(),
            account_reference=batch.account_reference.strip(),
            period_start=batch.period_start,
            period_end=batch.period_end,
        )
        self._session.add(record)
        for transaction in batch.transactions:
            self._session.add(
                BankTransactionRecord(
                    id=uuid4(),
                    import_batch_id=batch_id,
                    firm_id=batch.firm_id,
                    client_id=batch.client_id,
                    provider_name=batch.provider_name.strip(),
                    account_reference=batch.account_reference.strip(),
                    source_transaction_id=transaction.source_transaction_id.strip(),
                    booking_date=transaction.booking_date,
                    value_date=transaction.value_date,
                    direction=transaction.direction.value,
                    amount=transaction.amount,
                    currency=transaction.normalized_currency,
                    description=transaction.description.strip(),
                    reference=transaction.reference,
                    counterparty_name=transaction.counterparty_name,
                )
            )
        return record

    def get_import_batch_by_provider_reference(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        provider_name: str,
        account_reference: str,
        provider_batch_reference: str,
    ) -> BankImportBatchRecord | None:
        statement = select(BankImportBatchRecord).where(
            BankImportBatchRecord.firm_id == firm_id,
            BankImportBatchRecord.client_id == client_id,
            BankImportBatchRecord.provider_name == provider_name,
            BankImportBatchRecord.account_reference == account_reference,
            BankImportBatchRecord.provider_batch_reference == provider_batch_reference,
        )
        return self._session.scalar(statement)

    def get_import_batch(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        import_batch_id: UUID,
    ) -> BankImportBatchRecord | None:
        statement = select(BankImportBatchRecord).where(
            BankImportBatchRecord.id == import_batch_id,
            BankImportBatchRecord.firm_id == firm_id,
            BankImportBatchRecord.client_id == client_id,
        )
        return self._session.scalar(statement)

    def list_import_batches(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
    ) -> list[BankImportBatchRecord]:
        statement = (
            select(BankImportBatchRecord)
            .where(
                BankImportBatchRecord.firm_id == firm_id,
                BankImportBatchRecord.client_id == client_id,
            )
            .order_by(
                BankImportBatchRecord.created_at.desc(),
                BankImportBatchRecord.id.desc(),
            )
        )
        return list(self._session.scalars(statement))

    def get_transaction_by_source_id(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        provider_name: str,
        account_reference: str,
        source_transaction_id: str,
    ) -> BankTransactionRecord | None:
        statement = select(BankTransactionRecord).where(
            BankTransactionRecord.firm_id == firm_id,
            BankTransactionRecord.client_id == client_id,
            BankTransactionRecord.provider_name == provider_name,
            BankTransactionRecord.account_reference == account_reference,
            BankTransactionRecord.source_transaction_id == source_transaction_id,
        )
        return self._session.scalar(statement)

    def get_transaction(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        bank_transaction_id: UUID,
    ) -> BankTransactionRecord | None:
        statement = select(BankTransactionRecord).where(
            BankTransactionRecord.id == bank_transaction_id,
            BankTransactionRecord.firm_id == firm_id,
            BankTransactionRecord.client_id == client_id,
        )
        return self._session.scalar(statement)

    def list_transactions_for_batch(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        import_batch_id: UUID,
    ) -> list[BankTransactionRecord]:
        statement = (
            select(BankTransactionRecord)
            .where(
                BankTransactionRecord.import_batch_id == import_batch_id,
                BankTransactionRecord.firm_id == firm_id,
                BankTransactionRecord.client_id == client_id,
            )
            .order_by(
                BankTransactionRecord.booking_date.asc(),
                BankTransactionRecord.source_transaction_id.asc(),
            )
        )
        return list(self._session.scalars(statement))

    def add_match_result(
        self,
        *,
        transaction: BankTransactionRecord,
        result: ReconciliationMatchResult,
    ) -> ReconciliationMatchRunRecord:
        if transaction.source_transaction_id != result.source_transaction_id:
            raise ValueError("match result source_transaction_id must match persisted transaction")

        run_id = uuid4()
        run = ReconciliationMatchRunRecord(
            id=run_id,
            bank_transaction_id=transaction.id,
            firm_id=transaction.firm_id,
            client_id=transaction.client_id,
            status=result.status.value,
            matcher_name=result.matcher_name,
            matcher_version=result.matcher_version,
        )
        self._session.add(run)
        self._session.flush()

        for candidate in result.candidates:
            target = candidate.target
            if target.firm_id != transaction.firm_id or target.client_id != transaction.client_id:
                raise ValueError("candidate target ownership must match bank transaction")
            self._session.add(
                ReconciliationCandidateRecord(
                    id=uuid4(),
                    match_run_id=run_id,
                    bank_transaction_id=transaction.id,
                    firm_id=transaction.firm_id,
                    client_id=transaction.client_id,
                    review_outcome_id=target.review_outcome_id,
                    decision_run_id=target.decision_run_id,
                    document_id=target.document_id,
                    score=candidate.score,
                    reasons_json=[reason.value for reason in candidate.reasons],
                    target_transaction_date=target.transaction_date,
                    target_direction=target.direction.value,
                    target_amount=target.amount,
                    target_currency=target.normalized_currency,
                    target_reference=target.reference,
                    target_counterparty_name=target.counterparty_name,
                )
            )
        return run

    def list_match_runs_for_transaction(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        bank_transaction_id: UUID,
    ) -> list[ReconciliationMatchRunRecord]:
        statement = (
            select(ReconciliationMatchRunRecord)
            .where(
                ReconciliationMatchRunRecord.bank_transaction_id == bank_transaction_id,
                ReconciliationMatchRunRecord.firm_id == firm_id,
                ReconciliationMatchRunRecord.client_id == client_id,
            )
            .order_by(
                ReconciliationMatchRunRecord.created_at.asc(),
                ReconciliationMatchRunRecord.id.asc(),
            )
        )
        return list(self._session.scalars(statement))

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

    def list_candidates_for_run(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        match_run_id: UUID,
    ) -> list[ReconciliationCandidateRecord]:
        statement = (
            select(ReconciliationCandidateRecord)
            .where(
                ReconciliationCandidateRecord.match_run_id == match_run_id,
                ReconciliationCandidateRecord.firm_id == firm_id,
                ReconciliationCandidateRecord.client_id == client_id,
            )
            .order_by(
                ReconciliationCandidateRecord.score.desc(),
                ReconciliationCandidateRecord.review_outcome_id.asc(),
            )
        )
        return list(self._session.scalars(statement))
