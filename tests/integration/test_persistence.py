from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from tests.conftest import IdentitySeed


def test_session_rollback_works(db_session: Session) -> None:
    repository = IdentityRepository(db_session)
    firm = repository.add_firm(name="Synthetic Rollback Firm")
    db_session.flush()
    firm_id = firm.id
    db_session.rollback()

    assert repository.get_client_for_firm(firm_id=firm_id, client_id=firm_id) is None
    assert db_session.get(type(firm), firm_id) is None


def test_unique_external_subject_constraint(db_session: Session) -> None:
    repository = IdentityRepository(db_session)
    repository.add_user(external_subject="duplicate-subject")
    repository.add_user(external_subject="duplicate-subject")
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_foreign_key_ownership_constraint_blocks_cross_firm_client_access(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    repository = IdentityRepository(db_session)
    repository.grant_client_access(
        membership_id=identity_seed.accountant_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.firm_b_client.id,
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_membership_uniqueness_per_user_and_firm(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    repository = IdentityRepository(db_session)
    repository.add_membership(
        user_id=identity_seed.accountant.id,
        firm_id=identity_seed.firm_a.id,
        role=Role.AUDITOR.value,
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
