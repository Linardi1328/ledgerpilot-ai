from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.identity import ClientAccess
from ledgerpilot.persistence.models.reconciliation import (
    BankImportBatchRecord,
    BankTransactionRecord,
    ReconciliationCandidateRecord,
    ReconciliationMatchRunRecord,
)
from ledgerpilot.persistence.models.review import ReviewOutcome
from ledgerpilot.persistence.repositories.reconciliation import ReconciliationRepository
from ledgerpilot.reconciliation.matching import DeterministicReconciliationMatcher
from ledgerpilot.reconciliation.types import (
    ApprovedReconciliationTarget,
    BankImportBatch,
    BankTransactionDirection,
    ImportedBankTransaction,
    ReconciliationCandidateStatus,
)
from ledgerpilot.review.states import ReviewOutcomeType, ReviewTaskStatus
from tests.integration.test_postgresql_accounting_constraints import (
    _assert_integrity_error,
    _seed_postgresql_accounting_constraint_data,
)
from tests.integration.test_postgresql_review_constraints import (
    _balanced_journal,
    _review_task,
)


@pytest.fixture(scope="module")
def postgresql_engine() -> Generator[Engine]:
    database_url = os.environ.get("LEDGERPILOT_DATABASE_URL")
    if not database_url:
        pytest.skip("LEDGERPILOT_DATABASE_URL is not set for PostgreSQL constraint tests")
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        pytest.skip("PostgreSQL constraint tests require a PostgreSQL database URL")
    engine = create_engine(database_url, future=True, hide_parameters=True)
    try:
        yield engine
    finally:
        engine.dispose()


def test_postgresql_enforces_bank_import_scope_and_cross_import_idempotency(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
        seed = _seed_postgresql_accounting_constraint_data(session)

        first_batch = _batch_record(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_batch_reference="synthetic-batch-001",
        )
        session.add(first_batch)
        session.commit()

        first_transaction = _transaction_record(
            batch=first_batch,
            source_transaction_id="synthetic-txn-001",
        )
        session.add(first_transaction)
        session.commit()

        _assert_integrity_error(
            session,
            _batch_record(
                firm_id=seed.firm_a.id,
                client_id=seed.client_a.id,
                provider_batch_reference="synthetic-batch-001",
            ),
        )

        second_batch = _batch_record(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_batch_reference="synthetic-batch-002",
        )
        session.add(second_batch)
        session.commit()

        _assert_integrity_error(
            session,
            _transaction_record(
                batch=second_batch,
                source_transaction_id="synthetic-txn-001",
            ),
        )

        wrong_client_transaction = _transaction_record(
            batch=second_batch,
            source_transaction_id="synthetic-txn-wrong-client",
        )
        wrong_client_transaction.client_id = seed.client_b_same_firm.id
        _assert_integrity_error(session, wrong_client_transaction)

        invalid_direction = _transaction_record(
            batch=second_batch,
            source_transaction_id="synthetic-txn-invalid-direction",
        )
        invalid_direction.direction = "outbound"
        _assert_integrity_error(session, invalid_direction)

        non_positive_amount = _transaction_record(
            batch=second_batch,
            source_transaction_id="synthetic-txn-zero",
        )
        non_positive_amount.amount = Decimal("0")
        _assert_integrity_error(session, non_positive_amount)

        other_account_batch = _batch_record(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_batch_reference="synthetic-batch-003",
            account_reference="SYN-BANK-002",
        )
        session.add(other_account_batch)
        session.commit()
        session.add(
            _transaction_record(
                batch=other_account_batch,
                source_transaction_id="synthetic-txn-001",
            )
        )
        session.commit()


def test_postgresql_enforces_match_run_and_candidate_lineage(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
        seed, outcome = _seed_approved_outcome(session)

        batch = _batch_record(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_batch_reference="synthetic-match-batch-001",
        )
        session.add(batch)
        session.commit()

        transaction = _transaction_record(
            batch=batch,
            source_transaction_id="synthetic-match-txn-001",
        )
        session.add(transaction)
        session.commit()

        invalid_status_run = _match_run_record(transaction=transaction)
        invalid_status_run.status = "reconciled"
        _assert_integrity_error(session, invalid_status_run)

        run = _match_run_record(transaction=transaction)
        session.add(run)
        session.commit()

        candidate = _candidate_record(
            run=run,
            transaction=transaction,
            outcome=outcome,
        )
        session.add(candidate)
        session.commit()

        _assert_integrity_error(
            session,
            _candidate_record(
                run=run,
                transaction=transaction,
                outcome=outcome,
            ),
        )

        wrong_scope_run = _match_run_record(transaction=transaction)
        session.add(wrong_scope_run)
        session.commit()
        wrong_scope_candidate = _candidate_record(
            run=wrong_scope_run,
            transaction=transaction,
            outcome=outcome,
        )
        wrong_scope_candidate.client_id = seed.client_b_same_firm.id
        _assert_integrity_error(session, wrong_scope_candidate)

        invalid_score_run = _match_run_record(transaction=transaction)
        session.add(invalid_score_run)
        session.commit()
        invalid_score_candidate = _candidate_record(
            run=invalid_score_run,
            transaction=transaction,
            outcome=outcome,
        )
        invalid_score_candidate.score = Decimal("1.1000")
        _assert_integrity_error(session, invalid_score_candidate)


def test_repository_persists_unmatched_and_candidate_runs_with_lineage(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
        seed, outcome = _seed_approved_outcome(session)
        repository = ReconciliationRepository(session)

        domain_transaction = ImportedBankTransaction(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            source_transaction_id="synthetic-repo-txn-001",
            booking_date=date(2026, 8, 20),
            direction=BankTransactionDirection.DEBIT,
            amount=Decimal("100.0000"),
            currency="myr",
            description="SYNTHETIC RECONCILIATION TRANSACTION",
            reference="SYN-INV-001",
            counterparty_name="Synthetic Supplier Sdn Bhd",
        )
        batch = BankImportBatch(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_name="synthetic_bank_feed",
            provider_version="1.0",
            provider_batch_reference="synthetic-repo-batch-001",
            account_reference="SYN-BANK-001",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            transactions=(domain_transaction,),
        )
        batch_record = repository.add_import_batch(batch)
        session.commit()

        persisted_transaction = repository.get_transaction_by_source_id(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_name="synthetic_bank_feed",
            account_reference="SYN-BANK-001",
            source_transaction_id="synthetic-repo-txn-001",
        )
        assert persisted_transaction is not None
        assert persisted_transaction.import_batch_id == batch_record.id
        assert persisted_transaction.amount == Decimal("100.0000")
        assert persisted_transaction.currency == "MYR"

        matcher = DeterministicReconciliationMatcher()
        unmatched = matcher.match(domain_transaction, ())
        repository.add_match_result(
            transaction=persisted_transaction,
            result=unmatched,
        )
        session.commit()

        target = ApprovedReconciliationTarget(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            review_outcome_id=outcome.id,
            decision_run_id=outcome.decision_run_id,
            document_id=outcome.document_id,
            transaction_date=date(2026, 8, 20),
            direction=BankTransactionDirection.DEBIT,
            amount=Decimal("100.0000"),
            currency="MYR",
            reference="SYN-INV-001",
            counterparty_name="Synthetic Supplier Sdn Bhd",
        )
        candidates_available = matcher.match(domain_transaction, (target,))
        candidate_run = repository.add_match_result(
            transaction=persisted_transaction,
            result=candidates_available,
        )
        session.commit()

        runs = repository.list_match_runs_for_transaction(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            bank_transaction_id=persisted_transaction.id,
        )
        assert [run.status for run in runs] == [
            ReconciliationCandidateStatus.UNMATCHED.value,
            ReconciliationCandidateStatus.CANDIDATES_AVAILABLE.value,
        ]
        assert all(run.matcher_name == matcher.matcher_name for run in runs)

        candidates = repository.list_candidates_for_run(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            match_run_id=candidate_run.id,
        )
        assert len(candidates) == 1
        assert candidates[0].review_outcome_id == outcome.id
        assert candidates[0].score == Decimal("1.0000")
        assert candidates[0].target_amount == Decimal("100.0000")
        assert candidates[0].target_currency == "MYR"
        assert "exact_amount" in candidates[0].reasons_json


def _seed_approved_outcome(session: Session):
    seed = _seed_postgresql_accounting_constraint_data(session)
    session.add(
        ClientAccess(
            membership_id=seed.membership_a.id,
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            is_active=True,
        )
    )
    session.commit()

    journal = _balanced_journal(seed.decision_a)
    session.add(journal)
    session.commit()

    task = _review_task(
        decision=seed.decision_a,
        creator_user_id=seed.user_a.id,
        creator_membership_id=seed.membership_a.id,
        owner_user_id=seed.user_a.id,
        owner_membership_id=seed.membership_a.id,
    )
    task.status = ReviewTaskStatus.APPROVED.value
    session.add(task)
    session.commit()

    outcome = ReviewOutcome(
        review_task_id=task.id,
        firm_id=task.firm_id,
        client_id=task.client_id,
        decision_run_id=task.decision_run_id,
        document_id=task.document_id,
        extraction_run_id=task.extraction_run_id,
        actor_user_id=seed.user_a.id,
        actor_membership_id=seed.membership_a.id,
        outcome_type=ReviewOutcomeType.APPROVED.value,
        proposed_journal_id=journal.id,
        source_correction_count=0,
        reason=None,
    )
    session.add(outcome)
    session.commit()
    return seed, outcome


def _batch_record(
    *,
    firm_id,
    client_id,
    provider_batch_reference: str,
    account_reference: str = "SYN-BANK-001",
) -> BankImportBatchRecord:
    return BankImportBatchRecord(
        id=uuid.uuid4(),
        firm_id=firm_id,
        client_id=client_id,
        provider_name="synthetic_bank_feed",
        provider_version="1.0",
        provider_batch_reference=provider_batch_reference,
        account_reference=account_reference,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        created_at=datetime.now(UTC),
    )


def _transaction_record(
    *,
    batch: BankImportBatchRecord,
    source_transaction_id: str,
) -> BankTransactionRecord:
    return BankTransactionRecord(
        id=uuid.uuid4(),
        import_batch_id=batch.id,
        firm_id=batch.firm_id,
        client_id=batch.client_id,
        provider_name=batch.provider_name,
        account_reference=batch.account_reference,
        source_transaction_id=source_transaction_id,
        booking_date=date(2026, 8, 20),
        value_date=date(2026, 8, 20),
        direction=BankTransactionDirection.DEBIT.value,
        amount=Decimal("100.0000"),
        currency="MYR",
        description="SYNTHETIC BANK TRANSACTION",
        reference="SYN-INV-001",
        counterparty_name="Synthetic Supplier Sdn Bhd",
        created_at=datetime.now(UTC),
    )


def _match_run_record(
    *,
    transaction: BankTransactionRecord,
) -> ReconciliationMatchRunRecord:
    return ReconciliationMatchRunRecord(
        id=uuid.uuid4(),
        bank_transaction_id=transaction.id,
        firm_id=transaction.firm_id,
        client_id=transaction.client_id,
        status=ReconciliationCandidateStatus.CANDIDATES_AVAILABLE.value,
        matcher_name="deterministic_exact_bank_matcher",
        matcher_version="1.0",
        created_at=datetime.now(UTC),
    )


def _candidate_record(
    *,
    run: ReconciliationMatchRunRecord,
    transaction: BankTransactionRecord,
    outcome: ReviewOutcome,
) -> ReconciliationCandidateRecord:
    return ReconciliationCandidateRecord(
        id=uuid.uuid4(),
        match_run_id=run.id,
        bank_transaction_id=transaction.id,
        firm_id=transaction.firm_id,
        client_id=transaction.client_id,
        review_outcome_id=outcome.id,
        decision_run_id=outcome.decision_run_id,
        document_id=outcome.document_id,
        score=Decimal("0.9000"),
        reasons_json=["exact_amount", "exact_currency", "exact_direction"],
        target_transaction_date=date(2026, 8, 20),
        target_direction=BankTransactionDirection.DEBIT.value,
        target_amount=Decimal("100.0000"),
        target_currency="MYR",
        target_reference="SYN-INV-001",
        target_counterparty_name="Synthetic Supplier Sdn Bhd",
        created_at=datetime.now(UTC),
    )
