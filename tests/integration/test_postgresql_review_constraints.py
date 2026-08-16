from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.identity import ClientAccess
from ledgerpilot.persistence.models.review import ReviewTask
from ledgerpilot.review.states import ReviewEscalationState, ReviewTaskStatus
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


def test_postgresql_enforces_review_task_scope_owner_and_state_constraints(
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

        invalid_status_decision = _persist_additional_decision(session, seed)
        invalid_status = _review_task(
            decision=invalid_status_decision,
            creator_user_id=seed.user_a.id,
            creator_membership_id=seed.membership_a.id,
            owner_user_id=seed.user_a.id,
            owner_membership_id=seed.membership_a.id,
        )
        invalid_status.status = "approved"
        _assert_integrity_error(session, invalid_status)

        inconsistent_escalation_decision = _persist_additional_decision(session, seed)
        inconsistent_escalation = _review_task(
            decision=inconsistent_escalation_decision,
            creator_user_id=seed.user_a.id,
            creator_membership_id=seed.membership_a.id,
            owner_user_id=seed.user_a.id,
            owner_membership_id=seed.membership_a.id,
        )
        inconsistent_escalation.escalation_state = ReviewEscalationState.SENIOR_REVIEW.value
        inconsistent_escalation.escalated_at = datetime.now(UTC)
        _assert_integrity_error(session, inconsistent_escalation)

        escalated_without_state_decision = _persist_additional_decision(session, seed)
        escalated_without_state = _review_task(
            decision=escalated_without_state_decision,
            creator_user_id=seed.user_a.id,
            creator_membership_id=seed.membership_a.id,
            owner_user_id=seed.user_a.id,
            owner_membership_id=seed.membership_a.id,
        )
        escalated_without_state.status = ReviewTaskStatus.ESCALATED.value
        _assert_integrity_error(session, escalated_without_state)


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
        escalation_state=ReviewEscalationState.NONE.value,
        escalated_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
