from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.identity import ClientEntity
from ledgerpilot.persistence.repositories.identity import IdentityRepository


class ClientRepository:
    def __init__(self, session: Session) -> None:
        self._identity_repository = IdentityRepository(session)

    def get_client_for_firm(self, *, firm_id: UUID, client_id: UUID) -> ClientEntity | None:
        return self._identity_repository.get_client_for_firm(firm_id=firm_id, client_id=client_id)

    def get_authorized_client(
        self,
        *,
        membership_id: UUID,
        firm_id: UUID,
        client_id: UUID,
    ) -> ClientEntity | None:
        return self._identity_repository.get_authorized_client(
            membership_id=membership_id,
            firm_id=firm_id,
            client_id=client_id,
        )
