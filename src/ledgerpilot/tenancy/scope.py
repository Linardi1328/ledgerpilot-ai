from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ledgerpilot.identity.authorization import has_client_access
from ledgerpilot.identity.principal import Principal


class TenantScopeError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class FirmScope:
    firm_id: UUID


@dataclass(frozen=True, slots=True)
class ClientScope:
    firm_id: UUID
    client_id: UUID


def require_firm_scope(principal: Principal, firm_id: UUID) -> FirmScope:
    if principal.firm_id != firm_id:
        raise TenantScopeError("principal is not scoped to the requested firm")
    return FirmScope(firm_id=firm_id)


def require_client_scope(principal: Principal, client_id: UUID) -> ClientScope:
    if not has_client_access(principal, client_id):
        raise TenantScopeError("principal is not authorised for the requested client")
    return ClientScope(firm_id=principal.firm_id, client_id=client_id)
