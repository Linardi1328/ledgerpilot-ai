"""Fail-closed contracts for future LedgerPilot AI operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AiActionRisk(str, Enum):
    READ = "read"
    PROPOSE = "propose"
    MUTATE = "mutate"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class AiOperationRequest:
    operation: str
    risk: AiActionRisk
    source_record_ids: tuple[str, ...]
    approval_token: str | None = None


@dataclass(frozen=True)
class AiOperationResult:
    operation: str
    explanation: str
    source_record_ids: tuple[str, ...]
    executed: bool = False


def assert_action_allowed(request: AiOperationRequest) -> None:
    """Preserve deterministic accounting controls and explicit human approval."""
    if request.risk is AiActionRisk.RESTRICTED:
        raise PermissionError(f"AI operation {request.operation!r} is never autonomous")

    if request.risk is AiActionRisk.MUTATE and not request.approval_token:
        raise PermissionError(
            f"AI operation {request.operation!r} requires explicit human approval"
        )
