from __future__ import annotations

from sqlalchemy.orm import Session

from ledgerpilot.persistence.repositories.identity import IdentityRepository
from tests.conftest import IdentitySeed


def test_firm_a_cannot_access_firm_b_client(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    repository = IdentityRepository(db_session)
    result = repository.get_client_for_firm(
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.firm_b_client.id,
    )
    assert result is None


def test_client_a_access_does_not_imply_client_b_access(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    repository = IdentityRepository(db_session)
    allowed = repository.get_authorized_client(
        membership_id=identity_seed.accountant_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
    )
    denied = repository.get_authorized_client(
        membership_id=identity_seed.accountant_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_b.id,
    )
    assert allowed is not None
    assert denied is None


def test_cross_firm_client_lookup_fails_safely(
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    repository = IdentityRepository(db_session)
    result = repository.get_authorized_client(
        membership_id=identity_seed.accountant_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.firm_b_client.id,
    )
    assert result is None
