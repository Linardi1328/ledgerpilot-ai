from __future__ import annotations

import pytest

from ledgerpilot.extraction.states import (
    ExtractionRunStatus,
    InvalidExtractionTransition,
    is_extraction_ready_for_downstream,
    transition_extraction_status,
)


def test_extraction_lifecycle_allows_success_path() -> None:
    assert (
        transition_extraction_status(ExtractionRunStatus.PENDING, ExtractionRunStatus.RUNNING)
        is ExtractionRunStatus.RUNNING
    )
    assert (
        transition_extraction_status(ExtractionRunStatus.RUNNING, ExtractionRunStatus.SUCCEEDED)
        is ExtractionRunStatus.SUCCEEDED
    )


def test_extraction_lifecycle_allows_failure_path() -> None:
    assert (
        transition_extraction_status(ExtractionRunStatus.RUNNING, ExtractionRunStatus.FAILED)
        is ExtractionRunStatus.FAILED
    )


def test_terminal_extraction_run_cannot_restart() -> None:
    with pytest.raises(InvalidExtractionTransition):
        transition_extraction_status(ExtractionRunStatus.SUCCEEDED, ExtractionRunStatus.RUNNING)
    with pytest.raises(InvalidExtractionTransition):
        transition_extraction_status(ExtractionRunStatus.FAILED, ExtractionRunStatus.RUNNING)


def test_only_succeeded_extraction_is_downstream_ready() -> None:
    assert not is_extraction_ready_for_downstream(ExtractionRunStatus.PENDING)
    assert not is_extraction_ready_for_downstream(ExtractionRunStatus.RUNNING)
    assert not is_extraction_ready_for_downstream(ExtractionRunStatus.FAILED)
    assert is_extraction_ready_for_downstream(ExtractionRunStatus.SUCCEEDED)
