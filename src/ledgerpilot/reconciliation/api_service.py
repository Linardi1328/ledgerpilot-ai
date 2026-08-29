from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.accounting.service import build_effective_extraction_values
from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.service import AuditService
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.reconciliation import (
    BankImportBatchRecord,
    BankTransactionRecord,
    ReconciliationCandidateRecord,
    ReconciliationMatchRunRecord,
)
from ledgerpilot.persistence.repositories.accounting import AccountingRepository
from ledgerpilot.persistence.repositories.clients import ClientRepository
from ledgerpilot.persistence.repositories.extraction import ExtractionRepository
from ledgerpilot.persistence.repositories.reconciliation import ReconciliationRepository
from ledgerpilot.persistence.repositories.review import ReviewRepository
from ledgerpilot.reconciliation.matching import DeterministicReconciliationMatcher
from ledgerpilot.reconciliation.targets import project_approved_reconciliation_target
from ledgerpilot.reconciliation.types import (
    ApprovedReconciliationTarget,
    BankImportBatch,
    BankTransactionDirection,
    ImportedBankTransaction,
)

SYNTHETIC_API_PROVIDER_NAME = "synthetic_bank_feed"
SYNTHETIC_API_PROVIDER_VERSION = "1.0"


@dataclass(frozen=True)
class BankImportPersistenceResult:
    batch: BankImportBatchRecord
    transactions: tuple[BankTransactionRecord, ...]
    created: bool


@dataclass(frozen=True)
class ReconciliationMatchBundle:
    run: ReconciliationMatchRunRecord
    candidates: tuple[ReconciliationCandidateRecord, ...]


class ReconciliationApiService:
    def __init__(self, *, session: Session) -> None:
        self._session = session
        self._clients = ClientRepository(session)
        self._reconciliation = ReconciliationRepository(session)
        self._reviews = ReviewRepository(session)
        self._accounting = AccountingRepository(session)
        self._extractions = ExtractionRepository(session)
        self._audit = AuditService(session)

    def persist_import_batch(
        self,
        *,
        principal: Principal,
        batch: BankImportBatch,
        request_id: str | None,
    ) -> BankImportPersistenceResult:
        self._require_client_access(principal=principal, client_id=batch.client_id)
        if batch.firm_id != principal.firm_id:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

        existing = self._reconciliation.get_import_batch_by_provider_reference(
            firm_id=principal.firm_id,
            client_id=batch.client_id,
            provider_name=batch.provider_name.strip(),
            account_reference=batch.account_reference.strip(),
            provider_batch_reference=batch.provider_batch_reference.strip(),
        )
        if existing is not None:
            transactions = tuple(
                self._reconciliation.list_transactions_for_batch(
                    firm_id=principal.firm_id,
                    client_id=batch.client_id,
                    import_batch_id=existing.id,
                )
            )
            if not self._matches_existing_batch(
                batch=batch,
                existing_batch=existing,
                existing_transactions=transactions,
            ):
                raise ApiError(
                    status_code=409,
                    code="bank_import_batch_conflict",
                    message="The provider batch reference already exists with different data.",
                )
            return BankImportPersistenceResult(
                batch=existing,
                transactions=transactions,
                created=False,
            )

        for transaction in batch.transactions:
            already_imported = self._reconciliation.get_transaction_by_source_id(
                firm_id=principal.firm_id,
                client_id=batch.client_id,
                provider_name=batch.provider_name.strip(),
                account_reference=batch.account_reference.strip(),
                source_transaction_id=transaction.source_transaction_id.strip(),
            )
            if already_imported is not None:
                raise ApiError(
                    status_code=409,
                    code="bank_transaction_already_imported",
                    message="A bank transaction with this provider identity already exists.",
                )

        record = self._reconciliation.add_import_batch(batch)
        self._audit.record_event(
            firm_id=principal.firm_id,
            client_id=batch.client_id,
            actor_user_id=principal.user_id,
            event_type=AuditEventType.BANK_IMPORT_RECORDED.value,
            target_type="bank_import_batch",
            target_id=str(record.id),
            request_id=request_id,
            metadata={
                "provider_name": batch.provider_name.strip(),
                "provider_version": batch.provider_version.strip(),
                "provider_batch_reference": batch.provider_batch_reference.strip(),
                "transaction_count": len(batch.transactions),
            },
        )
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ApiError(
                status_code=409,
                code="bank_import_conflict",
                message="The bank import conflicts with existing provider transaction identity.",
            ) from exc

        transactions = tuple(
            self._reconciliation.list_transactions_for_batch(
                firm_id=principal.firm_id,
                client_id=batch.client_id,
                import_batch_id=record.id,
            )
        )
        return BankImportPersistenceResult(
            batch=record,
            transactions=transactions,
            created=True,
        )

    def generate_match_run(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        request_id: str | None,
    ) -> ReconciliationMatchBundle:
        transaction = self.get_transaction(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        targets = self._approved_targets(
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        result = DeterministicReconciliationMatcher().match(
            _transaction_value(transaction),
            targets,
        )
        run = self._reconciliation.add_match_result(transaction=transaction, result=result)
        self._audit.record_event(
            firm_id=principal.firm_id,
            client_id=client_id,
            actor_user_id=principal.user_id,
            event_type=AuditEventType.RECONCILIATION_MATCH_GENERATED.value,
            target_type="reconciliation_match_run",
            target_id=str(run.id),
            request_id=request_id,
            metadata={
                "bank_transaction_id": str(transaction.id),
                "status": result.status.value,
                "candidate_count": len(result.candidates),
                "matcher_name": result.matcher_name,
                "matcher_version": result.matcher_version,
            },
        )
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise ApiError(
                status_code=503,
                code="reconciliation_persistence_failed",
                message="Reconciliation match evidence could not be persisted.",
            ) from exc

        candidates = tuple(
            self._reconciliation.list_candidates_for_run(
                firm_id=principal.firm_id,
                client_id=client_id,
                match_run_id=run.id,
            )
        )
        return ReconciliationMatchBundle(run=run, candidates=candidates)

    def list_import_batches(
        self,
        *,
        principal: Principal,
        client_id: UUID,
    ) -> list[BankImportBatchRecord]:
        self._require_client_access(principal=principal, client_id=client_id)
        return self._reconciliation.list_import_batches(
            firm_id=principal.firm_id,
            client_id=client_id,
        )

    def get_import_batch(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        import_batch_id: UUID,
    ) -> BankImportBatchRecord:
        self._require_client_access(principal=principal, client_id=client_id)
        batch = self._reconciliation.get_import_batch(
            firm_id=principal.firm_id,
            client_id=client_id,
            import_batch_id=import_batch_id,
        )
        if batch is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return batch

    def list_transactions_for_batch(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        import_batch_id: UUID,
    ) -> list[BankTransactionRecord]:
        self.get_import_batch(
            principal=principal,
            client_id=client_id,
            import_batch_id=import_batch_id,
        )
        return self._reconciliation.list_transactions_for_batch(
            firm_id=principal.firm_id,
            client_id=client_id,
            import_batch_id=import_batch_id,
        )

    def get_transaction(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
    ) -> BankTransactionRecord:
        self._require_client_access(principal=principal, client_id=client_id)
        transaction = self._reconciliation.get_transaction(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        if transaction is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return transaction

    def list_match_runs(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
    ) -> list[ReconciliationMatchRunRecord]:
        self.get_transaction(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        return self._reconciliation.list_match_runs_for_transaction(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )

    def list_candidates(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        bank_transaction_id: UUID,
        match_run_id: UUID,
    ) -> list[ReconciliationCandidateRecord]:
        self.get_transaction(
            principal=principal,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
        )
        run = self._reconciliation.get_match_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            bank_transaction_id=bank_transaction_id,
            match_run_id=match_run_id,
        )
        if run is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return self._reconciliation.list_candidates_for_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            match_run_id=match_run_id,
        )

    def _approved_targets(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
    ) -> tuple[ApprovedReconciliationTarget, ...]:
        targets: list[ApprovedReconciliationTarget] = []
        for outcome in self._reviews.list_approved_outcomes_for_client(
            firm_id=firm_id,
            client_id=client_id,
        ):
            fields = self._extractions.list_fields_for_run(
                firm_id=firm_id,
                client_id=client_id,
                document_id=outcome.document_id,
                run_id=outcome.extraction_run_id,
            )
            corrections = self._extractions.list_corrections_for_run(
                firm_id=firm_id,
                client_id=client_id,
                document_id=outcome.document_id,
                run_id=outcome.extraction_run_id,
            )
            journal = self._accounting.get_proposed_journal_for_run(
                firm_id=firm_id,
                client_id=client_id,
                document_id=outcome.document_id,
                extraction_run_id=outcome.extraction_run_id,
                decision_run_id=outcome.decision_run_id,
            )
            target = project_approved_reconciliation_target(
                outcome=outcome,
                journal=journal,
                effective_values=build_effective_extraction_values(fields, corrections),
            )
            if target is not None:
                targets.append(target)
        return tuple(targets)

    def _require_client_access(self, *, principal: Principal, client_id: UUID) -> None:
        client = self._clients.get_authorized_client(
            membership_id=principal.membership_id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _matches_existing_batch(
        self,
        *,
        batch: BankImportBatch,
        existing_batch: BankImportBatchRecord,
        existing_transactions: tuple[BankTransactionRecord, ...],
    ) -> bool:
        if (
            existing_batch.provider_version != batch.provider_version.strip()
            or existing_batch.period_start != batch.period_start
            or existing_batch.period_end != batch.period_end
            or len(existing_transactions) != len(batch.transactions)
        ):
            return False

        existing_by_source_id = {
            transaction.source_transaction_id: transaction for transaction in existing_transactions
        }
        for transaction in batch.transactions:
            persisted = existing_by_source_id.get(transaction.source_transaction_id.strip())
            if persisted is None:
                return False
            if (
                persisted.booking_date != transaction.booking_date
                or persisted.value_date != transaction.value_date
                or persisted.direction != transaction.direction.value
                or Decimal(persisted.amount) != transaction.amount
                or persisted.currency != transaction.normalized_currency
                or persisted.description != transaction.description.strip()
                or persisted.reference != transaction.reference
                or persisted.counterparty_name != transaction.counterparty_name
            ):
                return False
        return True


def _transaction_value(record: BankTransactionRecord) -> ImportedBankTransaction:
    return ImportedBankTransaction(
        firm_id=record.firm_id,
        client_id=record.client_id,
        source_transaction_id=record.source_transaction_id,
        booking_date=record.booking_date,
        value_date=record.value_date,
        direction=BankTransactionDirection(record.direction),
        amount=Decimal(record.amount),
        currency=record.currency,
        description=record.description,
        reference=record.reference,
        counterparty_name=record.counterparty_name,
    )
