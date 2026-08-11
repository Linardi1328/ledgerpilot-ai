from __future__ import annotations

from enum import StrEnum


class AuditEventType(StrEnum):
    INFRASTRUCTURE_EVENT = "infrastructure.event"
    AUTHENTICATION_CONTEXT_READ = "authentication.context_read"
