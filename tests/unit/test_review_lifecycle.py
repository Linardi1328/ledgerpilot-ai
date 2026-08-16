from __future__ import annotations

import pytest

from ledgerpilot.review.states import (
    InvalidReviewTaskTransition,
    ReviewTaskStatus,
    transition_review_task_status,
)


def test_review_task_lifecycle_allows_only_senior_escalation() -> None:
    assert (
        transition_review_task_status(ReviewTaskStatus.OPEN, ReviewTaskStatus.ESCALATED)
        == ReviewTaskStatus.ESCALATED
    )


def test_review_task_lifecycle_rejects_invalid_and_terminal_transitions() -> None:
    with pytest.raises(InvalidReviewTaskTransition):
        transition_review_task_status(ReviewTaskStatus.OPEN, ReviewTaskStatus.OPEN)
    with pytest.raises(InvalidReviewTaskTransition):
        transition_review_task_status(ReviewTaskStatus.ESCALATED, ReviewTaskStatus.OPEN)
    with pytest.raises(InvalidReviewTaskTransition):
        transition_review_task_status(ReviewTaskStatus.ESCALATED, ReviewTaskStatus.ESCALATED)
