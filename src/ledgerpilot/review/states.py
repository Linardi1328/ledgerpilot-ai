from __future__ import annotations

from enum import StrEnum


class ReviewTaskStatus(StrEnum):
    OPEN = "open"
    ESCALATED = "escalated"


class ReviewEscalationState(StrEnum):
    NONE = "none"
    SENIOR_REVIEW = "senior_review"


_ALLOWED_TRANSITIONS: dict[ReviewTaskStatus, frozenset[ReviewTaskStatus]] = {
    ReviewTaskStatus.OPEN: frozenset({ReviewTaskStatus.ESCALATED}),
    ReviewTaskStatus.ESCALATED: frozenset(),
}


class InvalidReviewTaskTransition(ValueError):
    pass


def transition_review_task_status(
    current_status: ReviewTaskStatus,
    next_status: ReviewTaskStatus,
) -> ReviewTaskStatus:
    if next_status not in _ALLOWED_TRANSITIONS[current_status]:
        raise InvalidReviewTaskTransition(
            f"invalid review task transition: {current_status.value} -> {next_status.value}"
        )
    return next_status
