from __future__ import annotations

from enum import StrEnum


class ReviewTaskStatus(StrEnum):
    OPEN = "open"
    ESCALATED = "escalated"
    INFORMATION_REQUESTED = "information_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewEscalationState(StrEnum):
    NONE = "none"
    SENIOR_REVIEW = "senior_review"


class ReviewRiskClass(StrEnum):
    ORDINARY = "ordinary"
    SENIOR_REVIEW_REQUIRED = "senior_review_required"
    BLOCKED = "blocked"


class ReviewCommentKind(StrEnum):
    COMMENT = "comment"
    ESCALATION_REASON = "escalation_reason"
    INFORMATION_REQUEST = "information_request"
    INFORMATION_RESPONSE = "information_response"


class ReviewOutcomeType(StrEnum):
    APPROVED = "approved"
    CORRECTED_AND_APPROVED = "corrected_and_approved"
    REJECTED = "rejected"


_ALLOWED_TRANSITIONS: dict[ReviewTaskStatus, frozenset[ReviewTaskStatus]] = {
    ReviewTaskStatus.OPEN: frozenset(
        {
            ReviewTaskStatus.ESCALATED,
            ReviewTaskStatus.INFORMATION_REQUESTED,
            ReviewTaskStatus.APPROVED,
            ReviewTaskStatus.REJECTED,
        }
    ),
    ReviewTaskStatus.ESCALATED: frozenset(
        {
            ReviewTaskStatus.INFORMATION_REQUESTED,
            ReviewTaskStatus.APPROVED,
            ReviewTaskStatus.REJECTED,
        }
    ),
    ReviewTaskStatus.INFORMATION_REQUESTED: frozenset(
        {
            ReviewTaskStatus.OPEN,
            ReviewTaskStatus.ESCALATED,
            ReviewTaskStatus.REJECTED,
        }
    ),
    ReviewTaskStatus.APPROVED: frozenset(),
    ReviewTaskStatus.REJECTED: frozenset(),
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


def is_terminal_review_status(status: ReviewTaskStatus) -> bool:
    return status in {ReviewTaskStatus.APPROVED, ReviewTaskStatus.REJECTED}
