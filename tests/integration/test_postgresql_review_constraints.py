from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from ledgerpilot.accounting.types import JournalBalanceStatus
from ledgerpilot.persistence.models.accounting import ProposedJournal
from ledgerpilot.persistence.models.identity import ClientAccess
from ledgerpilot.persistence.models.review import ReviewComment, ReviewOutcome, ReviewTask
from ledgerpilot.review.states import (
    ReviewCommentKind,
    ReviewEscalationState,
    ReviewOutcomeType,
    ReviewRiskClass,
    ReviewTaskStatus,
)
from tests.integration.test_postgresql_accounting_constraints import (
    _assert_integrity_error,
    _persist_additional_decision,
    _seed_postgresql_accounting_constraint_data,
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


def test_postgresql_enforces_review_scope_state_history_and_outcome_constraints(
    postgresql_engine: Engine,
) -> None:
    with Session(postgresql_engine, expire_on_commit=False) as session:
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
        valid = _review_task(
            decision=seed.decision_a,
            creator_user_id=seed.user_a.id,
            creator_membership_id=seed.membership_a.id,
            owner_user_id=seed.user_a.id,
            owner_membership_id=seed.membership_a.id,
        )
        session.add(valid)
        session.commit()

        wrong_scope_decision = _persist_additional_decision(session, seed)
        wrong_scope = _review_task(
            decision=wrong_scope_decision,
            creator_user_id=seed.user_a.id,
            creator_membership_id=seed.membership_a.id,
            owner_user_id=seed.user_a.id,
            owner_membership_id=seed.membership_a.id,
        )
        wrong_scope.client_id = seed.client_b_same_firm.id
        _assert_integrity_error(session, wrong_scope)

        wrong_owner_decision = _persist_additional_decision(session, seed)
        _assert_integrity_error(
            session,
            _review_task(
                decision=wrong_owner_decision,
                creator_user_id=seed.user_a.id,
                creator_membership_id=seed.membership_a.id,
                owner_user_id=seed.user_firm_b.id,
                owner_membership_id=seed.membership_firm_b.id,
            ),
        )

        invalid_risk_decision = _persist_additional_decision(session, seed)
        invalid_risk = _review_task(
            decision=invalid_risk_decision,
            creator_user_id=seed.user_a.id,
            creator_membership_id=seed.membership_a.id,
            owner_user_id=seed.user_a.id,
            owner_membership_id=seed.membership_a.id,
        )
        invalid_risk.risk_class = "auto_approved"
        _assert_integrity_error(session, invalid_risk)

        invalid_status_decision = _persist_additional_decision(session, seed)
        invalid_status = _review_task(
            decision=invalid_status_decision,
            creator_user_id=seed.user_a.id,
            creator_membership_id=seed.membership_a.id,
            owner_user_id=seed.user_a.id,
            owner_membership_id=seed.membership_a.id,
        )
        invalid_status.status = "posted"
        _assert_integrity_error(session, invalid_status)

        inconsistent_state_decision = _persist_additional_decision(session, seed)
        inconsistent_state = _review_task(
            decision=inconsistent_state_decision,
            creator_user_id=seed.user_a.id,
            creator_membership_id=seed.membership_a.id,
            owner_user_id=seed.user_a.id,
            owner_membership_id=seed.membership_a.id,
        )
        inconsistent_state.status = ReviewTaskStatus.ESCALATED.value
        _assert_integrity_error(session, inconsistent_state)

        _assert_integrity_error(
            session,
            ReviewComment(
                review_task_id=valid.id,
                firm_id=valid.firm_id,
                client_id=valid.client_id,
                decision_run_id=valid.decision_run_id,
                author_user_id=seed.user_a.id,
                author_membership_id=seed.membership_a.id,
                kind="private_secret",
                body="Synthetic invalid comment kind.",
            ),
        )
        session.add(
            ReviewComment(
                review_task_id=valid.id,
                firm_id=valid.firm_id,
                client_id=valid.client_id,
                decision_run_id=valid.decision_run_id,
                author_user_id=seed.user_a.id,
                author_membership_id=seed.membership_a.id,
                kind=ReviewCommentKind.COMMENT.value,
                body="Synthetic review note.",
            )
        )
        session.commit()

        _assert_integrity_error(
            session,
            ReviewOutcome(
                review_task_id=valid.id,
                firm_id=valid.firm_id,
                client_id=valid.client_id,
                decision_run_id=valid.decision_run_id,
                document_id=valid.document_id,
                extraction_run_id=valid.extraction_run_id,
                actor_user_id=seed.user_a.id,
                actor_membership_id=seed.membership_a.id,
                outcome_type=ReviewOutcomeType.REJECTED.value,
                proposed_journal_id=None,
                source_correction_count=0,
                reason=None,
            ),
        )
        approved = ReviewOutcome(
            review_task_id=valid.id,
            firm_id=valid.firm_id,
            client_id=valid.client_id,
            decision_run_id=valid.decision_run_id,
            document_id=valid.document_id,
            extraction_run_id=valid.extraction_run_id,
            actor_user_id=seed.user_a.id,
            actor_membership_id=seed.membership_a.id,
            outcome_type=ReviewOutcomeType.APPROVED.value,
            proposed_journal_id=journal.id,
            source_correction_count=0,
            reason=None,
        )
        session.add(approved)
        session.commit()
        _assert_integrity_error(
            session,
            ReviewOutcome(
                review_task_id=valid.id,
                firm_id=valid.firm_id,
                client_id=valid.client_id,
                decision_run_id=valid.decision_run_id,
                document_id=valid.document_id,
                extraction_run_id=valid.extraction_run_id,
                actor_user_id=seed.user_a.id,
                actor_membership_id=seed.membership_a.id,
                outcome_type=ReviewOutcomeType.APPROVED.value,
                proposed_journal_id=journal.id,
                source_correction_count=0,
                reason=None,
            ),
        )


def _review_task(
    *,
    decision,
    creator_user_id,
    creator_membership_id,
    owner_user_id,
    owner_membership_id,
) -> ReviewTask:
    return ReviewTask(
        firm_id=decision.firm_id,
        client_id=decision.client_id,
        decision_run_id=decision.id,
        document_id=decision.document_id,
        extraction_run_id=decision.extraction_run_id,
        created_by_user_id=creator_user_id,
        created_by_membership_id=creator_membership_id,
        owner_user_id=owner_user_id,
        owner_membership_id=owner_membership_id,
        status=ReviewTaskStatus.OPEN.value,
        risk_class=ReviewRiskClass.ORDINARY.value,
        escalation_state=ReviewEscalationState.NONE.value,
        escalated_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _balanced_journal(decision) -> ProposedJournal:
    return ProposedJournal(
        decision_run_id=decision.id,
        firm_id=decision.firm_id,
        client_id=decision.client_id,
        document_id=decision.document_id,
        extraction_run_id=decision.extraction_run_id,
        currency="MYR",
        total_debits=Decimal("100.0000"),
        total_credits=Decimal("100.0000"),
        balance_status=JournalBalanceStatus.BALANCED.value,
        is_balanced=True,
        explanation="Synthetic review outcome journal.",
    )
