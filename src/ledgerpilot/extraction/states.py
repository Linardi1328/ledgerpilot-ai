from __future__ import annotations

from enum import StrEnum


class ExtractionRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


_ALLOWED_TRANSITIONS: dict[ExtractionRunStatus, frozenset[ExtractionRunStatus]] = {
    ExtractionRunStatus.PENDING: frozenset({ExtractionRunStatus.RUNNING}),
    ExtractionRunStatus.RUNNING: frozenset(
        {
            ExtractionRunStatus.SUCCEEDED,
            ExtractionRunStatus.FAILED,
        }
    ),
    ExtractionRunStatus.SUCCEEDED: frozenset(),
    ExtractionRunStatus.FAILED: frozenset(),
}


class InvalidExtractionTransition(ValueError):
    pass


def transition_extraction_status(
    current_status: ExtractionRunStatus,
    next_status: ExtractionRunStatus,
) -> ExtractionRunStatus:
    if next_status not in _ALLOWED_TRANSITIONS[current_status]:
        raise InvalidExtractionTransition(
            f"invalid extraction transition: {current_status.value} -> {next_status.value}"
        )
    return next_status


def is_extraction_ready_for_downstream(status: ExtractionRunStatus | str) -> bool:
    normalized = status if isinstance(status, ExtractionRunStatus) else ExtractionRunStatus(status)
    return normalized == ExtractionRunStatus.SUCCEEDED
