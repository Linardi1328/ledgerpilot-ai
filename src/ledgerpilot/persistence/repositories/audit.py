from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.audit import AuditEvent


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: AuditEvent) -> AuditEvent:
        self._session.add(event)
        return event

    def list_for_firm(self, *, firm_id: UUID) -> list[AuditEvent]:
        statement = (
            select(AuditEvent)
            .where(AuditEvent.firm_id == firm_id)
            .order_by(AuditEvent.occurred_at.asc())
        )
        return list(self._session.scalars(statement))

    def list_for_target(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        target_type: str,
        target_id: str,
    ) -> list[AuditEvent]:
        statement = (
            select(AuditEvent)
            .where(
                AuditEvent.firm_id == firm_id,
                AuditEvent.client_id == client_id,
                AuditEvent.target_type == target_type,
                AuditEvent.target_id == target_id,
            )
            .order_by(AuditEvent.occurred_at.asc(), AuditEvent.id.asc())
        )
        return list(self._session.scalars(statement))
