from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.roles import Role


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: UUID
    firm_id: UUID
    membership_id: UUID
    role: Role
    authorized_client_ids: frozenset[UUID]
    permissions: frozenset[Permission]
    request_id: str | None = None
