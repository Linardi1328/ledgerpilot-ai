from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from ledgerpilot.accounting.types import AccountingFindingCode, AccountingFindingSeverity
from ledgerpilot.review.states import ReviewRiskClass

_SENIOR_REVIEW_FINDING_CODES = frozenset(
    {
        AccountingFindingCode.POSSIBLE_DUPLICATE.value,
        AccountingFindingCode.NEW_SUPPLIER.value,
        AccountingFindingCode.LOW_EXTRACTION_CONFIDENCE.value,
        AccountingFindingCode.UNKNOWN_ACCOUNT_MAPPING.value,
    }
)


class ReviewFindingLike(Protocol):
    code: str
    severity: str


class ReviewJournalLike(Protocol):
    is_balanced: bool


def classify_review_risk(
    *,
    findings: Iterable[ReviewFindingLike],
    proposed_journal: ReviewJournalLike | None,
) -> ReviewRiskClass:
    materialized_findings = tuple(findings)
    if proposed_journal is None or not proposed_journal.is_balanced:
        return ReviewRiskClass.BLOCKED

    if any(
        finding.severity == AccountingFindingSeverity.ERROR.value
        for finding in materialized_findings
    ):
        return ReviewRiskClass.BLOCKED

    if any(finding.code in _SENIOR_REVIEW_FINDING_CODES for finding in materialized_findings):
        return ReviewRiskClass.SENIOR_REVIEW_REQUIRED

    return ReviewRiskClass.ORDINARY
