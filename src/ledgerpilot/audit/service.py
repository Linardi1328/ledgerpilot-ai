from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ledgerpilot.persistence.models.audit import AuditEvent
from ledgerpilot.persistence.repositories.audit import AuditRepository

SENSITIVE_METADATA_KEYS = frozenset(
    {
        "authorization",
        "api_key",
        "apikey",
        "bank_account",
        "credential",
        "password",
        "passwd",
        "private_key",
        "secret",
        "token",
    }
)


def _metadata_key_is_sensitive(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")
    compact = normalized.replace("_", "")
    return any(
        sensitive_key in normalized or sensitive_key.replace("_", "") in compact
        for sensitive_key in SENSITIVE_METADATA_KEYS
    )


class UnsafeAuditMetadataError(ValueError):
    pass


def _validate_metadata_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _validate_metadata(value)
    if isinstance(value, list):
        return [_validate_metadata_value(item) for item in value]
    if isinstance(value, tuple):
        return [_validate_metadata_value(item) for item in value]
    return value


def _validate_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    safe_metadata: dict[str, Any] = {}
    for key, value in metadata.items():
        if _metadata_key_is_sensitive(key):
            raise UnsafeAuditMetadataError(f"audit metadata key is not allowed: {key}")
        safe_metadata[key] = _validate_metadata_value(value)
    return safe_metadata


class AuditService:
    def __init__(self, session: Session) -> None:
        self._repository = AuditRepository(session)

    def record_event(
        self,
        *,
        firm_id: UUID,
        event_type: str,
        target_type: str,
        target_id: str,
        actor_user_id: UUID | None = None,
        client_id: UUID | None = None,
        request_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            firm_id=firm_id,
            client_id=client_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            occurred_at=datetime.now(UTC),
            request_id=request_id,
            metadata_json=_validate_metadata(metadata or {}),
        )
        self._repository.append(event)
        return event
