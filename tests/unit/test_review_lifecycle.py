from __future__ import annotations

import pytest

from ledgerpilot.review.states import (
    InvalidReviewTaskTransition,
    ReviewTaskStatus,
    is_terminal_review_status,
    transition_review_task_status,
)


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        (ReviewTaskStatus.OPEN, ReviewTaskStatus.ESCALATED),
        (ReviewTaskStatus.OPEN, ReviewTaskStatus.INFORMATION_REQUESTED),
        (ReviewTaskStatus.OPEN, ReviewTaskStatus.APPROVED),
        (ReviewTaskStatus.OPEN, ReviewTaskStatus.REJECTED),
        (ReviewTaskStatus.ESCALATED, ReviewTaskStatus.INFORMATION_REQUESTED),
        (ReviewTaskStatus.ESCALATED, ReviewTaskStatus.APPROVED),
        (ReviewTaskStatus.ESCALATED, ReviewTaskStatus.REJECTED),
        (ReviewTaskStatus.INFORMATION_REQUESTED, ReviewTaskStatus.OPEN),
        (ReviewTaskStatus.INFORMATION_REQUESTED, ReviewTaskStatus.ESCALATED),
        (ReviewTaskStatus.INFORMATION_REQUESTED, ReviewTaskStatus.REJECTED),
    ],
)
def test_review_task_lifecycle_allows_defined_transitions(
    current_status: ReviewTaskStatus,
    next_status: ReviewTaskStatus,
) -> None:
    assert transition_review_task_status(current_status, next_status) == next_status


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        (ReviewTaskStatus.OPEN, ReviewTaskStatus.OPEN),
        (ReviewTaskStatus.ESCALATED, ReviewTaskStatus.OPEN),
        (ReviewTaskStatus.INFORMATION_REQUESTED, ReviewTaskStatus.APPROVED),
        (ReviewTaskStatus.APPROVED, ReviewTaskStatus.OPEN),
        (ReviewTaskStatus.APPROVED, ReviewTaskStatus.REJECTED),
        (ReviewTaskStatus.REJECTED, ReviewTaskStatus.OPEN),
        (ReviewTaskStatus.REJECTED, ReviewTaskStatus.APPROVED),
    ],
)
def test_review_task_lifecycle_rejects_undefined_and_terminal_transitions(
    current_status: ReviewTaskStatus,
    next_status: ReviewTaskStatus,
) -> None:
    with pytest.raises(InvalidReviewTaskTransition):
        transition_review_task_status(current_status, next_status)


def test_terminal_review_statuses_are_explicit() -> None:
    assert is_terminal_review_status(ReviewTaskStatus.APPROVED)
    assert is_terminal_review_status(ReviewTaskStatus.REJECTED)
    assert not is_terminal_review_status(ReviewTaskStatus.OPEN)
