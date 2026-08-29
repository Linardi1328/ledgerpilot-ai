from __future__ import annotations

from dataclasses import dataclass

from ledgerpilot.accounting.types import AccountingFindingCode, AccountingFindingSeverity
from ledgerpilot.review.policy import classify_review_risk
from ledgerpilot.review.states import ReviewRiskClass


@dataclass(frozen=True)
class _Finding:
    code: str
    severity: str


@dataclass(frozen=True)
class _Journal:
    is_balanced: bool


def _finding(*, code: AccountingFindingCode, severity: AccountingFindingSeverity) -> _Finding:
    return _Finding(code=code.value, severity=severity.value)


def test_review_policy_allows_ordinary_human_review_for_nonblocking_warning() -> None:
    risk = classify_review_risk(
        findings=[
            _finding(
                code=AccountingFindingCode.TAX_REVIEW_REQUIRED,
                severity=AccountingFindingSeverity.WARNING,
            )
        ],
        proposed_journal=_Journal(is_balanced=True),
    )

    assert risk == ReviewRiskClass.ORDINARY


def test_review_policy_routes_material_warning_to_senior_review() -> None:
    risk = classify_review_risk(
        findings=[
            _finding(
                code=AccountingFindingCode.POSSIBLE_DUPLICATE,
                severity=AccountingFindingSeverity.WARNING,
            )
        ],
        proposed_journal=_Journal(is_balanced=True),
    )

    assert risk == ReviewRiskClass.SENIOR_REVIEW_REQUIRED


def test_review_policy_blocks_error_or_missing_or_unbalanced_journal() -> None:
    error_risk = classify_review_risk(
        findings=[
            _finding(
                code=AccountingFindingCode.MISSING_REQUIRED_FIELD,
                severity=AccountingFindingSeverity.ERROR,
            )
        ],
        proposed_journal=_Journal(is_balanced=True),
    )
    missing_journal_risk = classify_review_risk(findings=[], proposed_journal=None)
    unbalanced_risk = classify_review_risk(
        findings=[],
        proposed_journal=_Journal(is_balanced=False),
    )

    assert error_risk == ReviewRiskClass.BLOCKED
    assert missing_journal_risk == ReviewRiskClass.BLOCKED
    assert unbalanced_risk == ReviewRiskClass.BLOCKED
