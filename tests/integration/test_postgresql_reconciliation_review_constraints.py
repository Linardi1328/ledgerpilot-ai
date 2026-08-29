from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.reconciliation_review import (
    ReconciliationOutcomeRecord,
    ReconciliationReviewActionRecord,
    ReconciliationReviewRecord,
)
from ledgerpilot.reconciliation.states import (
    ReconciliationOutcomeType,
    ReconciliationReviewActionType,
    ReconciliationReviewStatus,
)
from tests.integration.test_postgresql_accounting_constraints import _assert_integrity_error
from tests.integration.test_postgresql_reconciliation_constraints import (
    _batch_record,
    _candidate_record,
    _match_run_record,
    _seed_approved_outcome,
    _transaction_record,
    postgresql_engine,
)


def test_postgresql_enforces_reconciliation_review_scope_and_terminal_uniqueness(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
        seed, approved_outcome = _seed_approved_outcome(session)

        first_batch = _batch_record(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_batch_reference="synthetic-review-batch-001",
        )
        session.add(first_batch)
        session.commit()

        first_transaction = _transaction_record(
            batch=first_batch,
            source_transaction_id="synthetic-review-txn-001",
        )
        session.add(first_transaction)
        session.commit()

        first_run = _match_run_record(transaction=first_transaction)
        session.add(first_run)
        session.commit()

        first_candidate = _candidate_record(
            run=first_run,
            transaction=first_transaction,
            outcome=approved_outcome,
        )
        session.add(first_candidate)
        session.commit()

        invalid_scope_review = _review_record(
            seed=seed,
            transaction=first_transaction,
            match_run_id=first_run.id,
        )
        invalid_scope_review.client_id = seed.client_b_same_firm.id
        _assert_integrity_error(session, invalid_scope_review)

        invalid_candidate_review = _review_record(
            seed=seed,
            transaction=first_transaction,
            match_run_id=first_run.id,
        )
        invalid_candidate_review.selected_review_outcome_id = uuid.uuid4()
        _assert_integrity_error(session, invalid_candidate_review)

        review = _review_record(
            seed=seed,
            transaction=first_transaction,
            match_run_id=first_run.id,
        )
        review.selected_review_outcome_id = approved_outcome.id
        session.add(review)
        session.commit()

        _assert_integrity_error(
            session,
            _review_record(
                seed=seed,
                transaction=first_transaction,
                match_run_id=first_run.id,
            ),
        )

        invalid_action = _action_record(
            seed=seed,
            review=review,
            action_type=ReconciliationReviewActionType.CANDIDATE_SELECTED.value,
            candidate_review_outcome_id=uuid.uuid4(),
        )
        _assert_integrity_error(session, invalid_action)

        session.add(
            _action_record(
                seed=seed,
                review=review,
                action_type=ReconciliationReviewActionType.CANDIDATE_SELECTED.value,
                candidate_review_outcome_id=approved_outcome.id,
            )
        )
        session.commit()

        matched_outcome = _outcome_record(
            seed=seed,
            review=review,
            outcome_type=ReconciliationOutcomeType.MATCHED.value,
            matched_review_outcome_id=approved_outcome.id,
            reason=None,
        )
        session.add(matched_outcome)
        session.commit()

        _assert_integrity_error(
            session,
            _outcome_record(
                seed=seed,
                review=review,
                outcome_type=ReconciliationOutcomeType.MATCHED.value,
                matched_review_outcome_id=approved_outcome.id,
                reason=None,
            ),
        )

        second_batch = _batch_record(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_batch_reference="synthetic-review-batch-002",
        )
        session.add(second_batch)
        session.commit()
        second_transaction = _transaction_record(
            batch=second_batch,
            source_transaction_id="synthetic-review-txn-002",
        )
        session.add(second_transaction)
        session.commit()
        second_run = _match_run_record(transaction=second_transaction)
        session.add(second_run)
        session.commit()
        second_candidate = _candidate_record(
            run=second_run,
            transaction=second_transaction,
            outcome=approved_outcome,
        )
        session.add(second_candidate)
        session.commit()
        second_review = _review_record(
            seed=seed,
            transaction=second_transaction,
            match_run_id=second_run.id,
        )
        second_review.selected_review_outcome_id = approved_outcome.id
        session.add(second_review)
        session.commit()

        _assert_integrity_error(
            session,
            _outcome_record(
                seed=seed,
                review=second_review,
                outcome_type=ReconciliationOutcomeType.MATCHED.value,
                matched_review_outcome_id=approved_outcome.id,
                reason=None,
            ),
        )

        unmatched_batch = _batch_record(
            firm_id=seed.firm_a.id,
            client_id=seed.client_a.id,
            provider_batch_reference="synthetic-review-batch-003",
        )
        session.add(unmatched_batch)
        session.commit()
        unmatched_transaction = _transaction_record(
            batch=unmatched_batch,
            source_transaction_id="synthetic-review-txn-003",
        )
        session.add(unmatched_transaction)
        session.commit()
        unmatched_run = _match_run_record(transaction=unmatched_transaction)
        session.add(unmatched_run)
        session.commit()
        unmatched_review = _review_record(
            seed=seed,
            transaction=unmatched_transaction,
            match_run_id=unmatched_run.id,
        )
        session.add(unmatched_review)
        session.commit()

        _assert_integrity_error(
            session,
            _outcome_record(
                seed=seed,
                review=unmatched_review,
                outcome_type=ReconciliationOutcomeType.UNMATCHED.value,
                matched_review_outcome_id=None,
                reason=None,
            ),
        )


def _review_record(*, seed, transaction, match_run_id) -> ReconciliationReviewRecord:
    return ReconciliationReviewRecord(
        id=uuid.uuid4(),
        bank_transaction_id=transaction.id,
        firm_id=transaction.firm_id,
        client_id=transaction.client_id,
        match_run_id=match_run_id,
        created_by_user_id=seed.user_a.id,
        created_by_membership_id=seed.membership_a.id,
        status=ReconciliationReviewStatus.OPEN.value,
        selected_review_outcome_id=None,
        request_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _action_record(
    *,
    seed,
    review: ReconciliationReviewRecord,
    action_type: str,
    candidate_review_outcome_id,
) -> ReconciliationReviewActionRecord:
    return ReconciliationReviewActionRecord(
        id=uuid.uuid4(),
        reconciliation_review_id=review.id,
        bank_transaction_id=review.bank_transaction_id,
        firm_id=review.firm_id,
        client_id=review.client_id,
        match_run_id=review.match_run_id,
        actor_user_id=seed.user_a.id,
        actor_membership_id=seed.membership_a.id,
        action_type=action_type,
        candidate_review_outcome_id=candidate_review_outcome_id,
        reason=None,
        request_id=None,
        created_at=datetime.now(UTC),
    )


def _outcome_record(
    *,
    seed,
    review: ReconciliationReviewRecord,
    outcome_type: str,
    matched_review_outcome_id,
    reason: str | None,
) -> ReconciliationOutcomeRecord:
    return ReconciliationOutcomeRecord(
        id=uuid.uuid4(),
        reconciliation_review_id=review.id,
        bank_transaction_id=review.bank_transaction_id,
        firm_id=review.firm_id,
        client_id=review.client_id,
        match_run_id=review.match_run_id,
        matched_review_outcome_id=matched_review_outcome_id,
        actor_user_id=seed.user_a.id,
        actor_membership_id=seed.membership_a.id,
        outcome_type=outcome_type,
        reason=reason,
        request_id=None,
        created_at=datetime.now(UTC),
    )
