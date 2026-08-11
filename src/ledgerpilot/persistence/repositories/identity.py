from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.identity import (
    ClientAccess,
    ClientEntity,
    Firm,
    FirmMembership,
    User,
)


class IdentityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_firm(self, *, name: str, status: str = "active") -> Firm:
        firm = Firm(name=name, status=status)
        self._session.add(firm)
        return firm

    def add_user(self, *, external_subject: str, is_active: bool = True) -> User:
        user = User(external_subject=external_subject, is_active=is_active)
        self._session.add(user)
        return user

    def add_membership(
        self,
        *,
        user_id: UUID,
        firm_id: UUID,
        role: str,
        is_active: bool = True,
    ) -> FirmMembership:
        membership = FirmMembership(
            user_id=user_id,
            firm_id=firm_id,
            role=role,
            is_active=is_active,
        )
        self._session.add(membership)
        return membership

    def add_client(
        self,
        *,
        firm_id: UUID,
        name: str,
        status: str = "active",
    ) -> ClientEntity:
        client = ClientEntity(firm_id=firm_id, name=name, status=status)
        self._session.add(client)
        return client

    def grant_client_access(
        self,
        *,
        membership_id: UUID,
        firm_id: UUID,
        client_id: UUID,
        is_active: bool = True,
    ) -> ClientAccess:
        access = ClientAccess(
            membership_id=membership_id,
            firm_id=firm_id,
            client_id=client_id,
            is_active=is_active,
        )
        self._session.add(access)
        return access

    def get_active_user_by_subject(self, external_subject: str) -> User | None:
        statement = select(User).where(
            User.external_subject == external_subject,
            User.is_active.is_(True),
        )
        return self._session.scalar(statement)

    def get_active_membership_for_firm(
        self,
        *,
        user_id: UUID,
        firm_id: UUID,
    ) -> FirmMembership | None:
        statement = select(FirmMembership).where(
            FirmMembership.user_id == user_id,
            FirmMembership.firm_id == firm_id,
            FirmMembership.is_active.is_(True),
        )
        return self._session.scalar(statement)

    def get_client_for_firm(self, *, firm_id: UUID, client_id: UUID) -> ClientEntity | None:
        statement = select(ClientEntity).where(
            ClientEntity.id == client_id,
            ClientEntity.firm_id == firm_id,
        )
        return self._session.scalar(statement)

    def get_authorized_client(
        self,
        *,
        membership_id: UUID,
        firm_id: UUID,
        client_id: UUID,
    ) -> ClientEntity | None:
        statement = (
            select(ClientEntity)
            .join(
                ClientAccess,
                (ClientAccess.client_id == ClientEntity.id)
                & (ClientAccess.firm_id == ClientEntity.firm_id),
            )
            .where(
                ClientEntity.id == client_id,
                ClientEntity.firm_id == firm_id,
                ClientAccess.membership_id == membership_id,
                ClientAccess.is_active.is_(True),
            )
        )
        return self._session.scalar(statement)

    def list_authorized_client_ids(self, *, membership_id: UUID, firm_id: UUID) -> list[UUID]:
        statement = select(ClientAccess.client_id).where(
            ClientAccess.membership_id == membership_id,
            ClientAccess.firm_id == firm_id,
            ClientAccess.is_active.is_(True),
        )
        return list(self._session.scalars(statement))
