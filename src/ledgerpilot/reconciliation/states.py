from __future__ import annotations

from enum import StrEnum


class ReconciliationReviewStatus(StrEnum):
    OPEN = "open"
    DISPUTED = "disputed"
    MATCHED = "matched"
    UNMATCHED = "unmatched"


class ReconciliationReviewActionType(StrEnum):
    CANDIDATE_SELECTED = "candidate_selected"
    DISPUTED = "disputed"
    REOPENED = "reopened"
    APPROVED_MATCH = "approved_match"
    MARKED_UNMATCHED = "marked_unmatched"


class ReconciliationOutcomeType(StrEnum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"


class ReconciliationWorkflowState(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    UNMATCHED = "unmatched"
    CANDIDATES_AVAILABLE = "candidates_available"
    IN_REVIEW = "in_review"
    DISPUTED = "disputed"
    MATCHED = "matched"
    RESOLVED_UNMATCHED = "resolved_unmatched"


TERMINAL_RECONCILIATION_REVIEW_STATUSES = frozenset(
    {
        ReconciliationReviewStatus.MATCHED,
        ReconciliationReviewStatus.UNMATCHED,
    }
)
