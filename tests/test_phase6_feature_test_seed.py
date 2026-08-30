from __future__ import annotations

import pytest

from ledgerpilot.identity.authorization import permissions_for_role
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.identity import User
from ledgerpilot.reconciliation.api_service import ReconciliationApiService
from ledgerpilot.reconciliation.states import ReconciliationWorkflowState
from ledgerpilot.reconciliation.types import ReconciliationCandidateStatus
from ledgerpilot.reconciliation.worklist import ReconciliationWorklistService
from tools.phase6_feature_test_seed import (
    CLIENT_A_ID,
    FIRM_ID,
    MEMBERSHIP_IDS,
    SUBJECTS,
    USER_IDS,
    seed_phase6_feature_test,
)


def _accountant_principal() -> Principal:
    return Principal(
        user_id=USER_IDS["accountant"],
        firm_id=FIRM_ID,
        membership_id=MEMBERSHIP_IDS["accountant"],
        role=Role.ACCOUNTANT,
        authorized_client_ids=frozenset({CLIENT_A_ID}),
        permissions=permissions_for_role(Role.ACCOUNTANT),
        request_id="phase6-feature-test-seed-test",
    )


def test_phase6_feature_test_seed_is_idempotent_and_drives_real_matching(
    db_session,
    settings,
) -> None:
    first = seed_phase6_feature_test(
        db_session,
        settings,
        confirm_synthetic_test_database=True,
        require_alembic_head=False,
    )
    second = seed_phase6_feature_test(
        db_session,
        settings,
        confirm_synthetic_test_database=True,
        require_alembic_head=False,
    )

    assert second == first
    accountant = db_session.get(User, USER_IDS["accountant"])
    assert accountant is not None
    assert accountant.external_subject == SUBJECTS["accountant"]

    principal = _accountant_principal()
    initial_items = ReconciliationWorklistService(session=db_session).list_items(
        principal=principal,
        client_id=CLIENT_A_ID,
        state=None,
        limit=50,
    )
    assert len(initial_items) == 3
    assert {item.workflow_state for item in initial_items} == {
        ReconciliationWorkflowState.NOT_EVALUATED
    }

    match = ReconciliationApiService(session=db_session).generate_match_run(
        principal=principal,
        client_id=CLIENT_A_ID,
        bank_transaction_id=first.candidate_transaction_id,
        request_id="phase6-feature-test-match",
    )
    assert match.run.status == ReconciliationCandidateStatus.CANDIDATES_AVAILABLE.value
    assert len(match.candidates) == 1
    assert match.candidates[0].review_outcome_id == first.approved_outcome_id

    unmatched = ReconciliationApiService(session=db_session).generate_match_run(
        principal=principal,
        client_id=CLIENT_A_ID,
        bank_transaction_id=first.unmatched_transaction_id,
        request_id="phase6-feature-test-unmatched",
    )
    assert unmatched.run.status == ReconciliationCandidateStatus.UNMATCHED.value
    assert not unmatched.candidates

    candidate_items = ReconciliationWorklistService(session=db_session).list_items(
        principal=principal,
        client_id=CLIENT_A_ID,
        state=ReconciliationWorkflowState.CANDIDATES_AVAILABLE,
        limit=50,
    )
    assert [item.transaction.id for item in candidate_items] == [
        first.candidate_transaction_id
    ]
    untouched_items = ReconciliationWorklistService(session=db_session).list_items(
        principal=principal,
        client_id=CLIENT_A_ID,
        state=ReconciliationWorkflowState.NOT_EVALUATED,
        limit=50,
    )
    assert [item.transaction.id for item in untouched_items] == [
        first.untouched_transaction_id
    ]


def test_phase6_feature_test_seed_requires_explicit_confirmation(db_session, settings) -> None:
    with pytest.raises(RuntimeError, match="confirmation"):
        seed_phase6_feature_test(
            db_session,
            settings,
            confirm_synthetic_test_database=False,
            require_alembic_head=False,
        )
