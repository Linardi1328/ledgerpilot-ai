from __future__ import annotations

import uuid

import pytest

from ledgerpilot.identity.authorization import permissions_for_role
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role
from ledgerpilot.tenancy.scope import TenantScopeError, require_client_scope, require_firm_scope


def test_firm_scope_accepts_matching_firm() -> None:
    firm_id = uuid.uuid4()
    principal = Principal(
        user_id=uuid.uuid4(),
        firm_id=firm_id,
        membership_id=uuid.uuid4(),
        role=Role.ACCOUNTANT,
        authorized_client_ids=frozenset(),
        permissions=permissions_for_role(Role.ACCOUNTANT),
    )
    assert require_firm_scope(principal, firm_id).firm_id == firm_id


def test_firm_scope_rejects_other_firm() -> None:
    principal = Principal(
        user_id=uuid.uuid4(),
        firm_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        role=Role.ACCOUNTANT,
        authorized_client_ids=frozenset(),
        permissions=permissions_for_role(Role.ACCOUNTANT),
    )
    with pytest.raises(TenantScopeError):
        require_firm_scope(principal, uuid.uuid4())


def test_client_scope_rejects_unauthorised_client() -> None:
    principal = Principal(
        user_id=uuid.uuid4(),
        firm_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        role=Role.ACCOUNTANT,
        authorized_client_ids=frozenset({uuid.uuid4()}),
        permissions=permissions_for_role(Role.ACCOUNTANT),
    )
    with pytest.raises(TenantScopeError):
        require_client_scope(principal, uuid.uuid4())
