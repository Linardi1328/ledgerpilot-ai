from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from ledgerpilot.reconciliation.types import (
    ApprovedReconciliationTarget,
    ImportedBankTransaction,
    ReconciliationCandidateDecision,
    ReconciliationCandidateStatus,
    ReconciliationMatchReason,
    ReconciliationMatchResult,
)

_TOKEN_PATTERN = re.compile(r"[A-Z0-9]+")


@dataclass(frozen=True)
class ReconciliationMatchingPolicy:
    date_window_days: int = 7
    minimum_candidate_score: Decimal = Decimal("0.60")
    same_date_score: Decimal = Decimal("0.20")
    near_date_score: Decimal = Decimal("0.08")
    exact_reference_score: Decimal = Decimal("0.15")
    reference_contains_score: Decimal = Decimal("0.08")
    exact_counterparty_score: Decimal = Decimal("0.10")
    base_exact_match_score: Decimal = Decimal("0.55")

    def __post_init__(self) -> None:
        if self.date_window_days < 0:
            raise ValueError("date_window_days must not be negative")
        decimal_fields = (
            self.minimum_candidate_score,
            self.same_date_score,
            self.near_date_score,
            self.exact_reference_score,
            self.reference_contains_score,
            self.exact_counterparty_score,
            self.base_exact_match_score,
        )
        if any(not isinstance(value, Decimal) for value in decimal_fields):
            raise TypeError("matching scores must use Decimal")
        if not Decimal("0") <= self.minimum_candidate_score <= Decimal("1"):
            raise ValueError("minimum_candidate_score must be between zero and one")


class DeterministicReconciliationMatcher:
    matcher_name = "deterministic_exact_bank_matcher"
    matcher_version = "1.0"

    def __init__(self, policy: ReconciliationMatchingPolicy | None = None) -> None:
        self.policy = policy or ReconciliationMatchingPolicy()

    def match(
        self,
        transaction: ImportedBankTransaction,
        targets: tuple[ApprovedReconciliationTarget, ...],
    ) -> ReconciliationMatchResult:
        candidates = [
            candidate
            for target in targets
            if (candidate := self._score_candidate(transaction, target)) is not None
        ]
        candidates.sort(
            key=lambda candidate: (-candidate.score, str(candidate.target.review_outcome_id))
        )

        if not candidates:
            return ReconciliationMatchResult(
                source_transaction_id=transaction.source_transaction_id,
                status=ReconciliationCandidateStatus.UNMATCHED,
                candidates=(),
            )

        return ReconciliationMatchResult(
            source_transaction_id=transaction.source_transaction_id,
            status=ReconciliationCandidateStatus.CANDIDATES_AVAILABLE,
            candidates=tuple(candidates),
        )

    def _score_candidate(
        self,
        transaction: ImportedBankTransaction,
        target: ApprovedReconciliationTarget,
    ) -> ReconciliationCandidateDecision | None:
        if transaction.firm_id != target.firm_id or transaction.client_id != target.client_id:
            return None
        if transaction.amount != target.amount:
            return None
        if transaction.normalized_currency != target.normalized_currency:
            return None
        if transaction.direction is not target.direction:
            return None

        date_delta = abs((transaction.booking_date - target.transaction_date).days)
        if date_delta > self.policy.date_window_days:
            return None

        score = self.policy.base_exact_match_score
        reasons: list[ReconciliationMatchReason] = [
            ReconciliationMatchReason.EXACT_AMOUNT,
            ReconciliationMatchReason.EXACT_CURRENCY,
            ReconciliationMatchReason.EXACT_DIRECTION,
        ]

        if date_delta == 0:
            score += self.policy.same_date_score
            reasons.append(ReconciliationMatchReason.SAME_DATE)
        else:
            score += self.policy.near_date_score
            reasons.append(ReconciliationMatchReason.NEAR_DATE)

        reference_score, reference_reason = self._reference_score(
            transaction.reference,
            target.reference,
        )
        score += reference_score
        if reference_reason is not None:
            reasons.append(reference_reason)

        if self._normalized_text(transaction.counterparty_name) and self._normalized_text(
            transaction.counterparty_name
        ) == self._normalized_text(target.counterparty_name):
            score += self.policy.exact_counterparty_score
            reasons.append(ReconciliationMatchReason.EXACT_COUNTERPARTY)

        score = min(score, Decimal("1"))
        if score < self.policy.minimum_candidate_score:
            return None

        return ReconciliationCandidateDecision(
            target=target,
            score=score,
            reasons=tuple(reasons),
            matcher_name=self.matcher_name,
            matcher_version=self.matcher_version,
        )

    def _reference_score(
        self,
        transaction_reference: str | None,
        target_reference: str | None,
    ) -> tuple[Decimal, ReconciliationMatchReason | None]:
        left = self._normalized_text(transaction_reference)
        right = self._normalized_text(target_reference)
        if not left or not right:
            return Decimal("0"), None
        if left == right:
            return self.policy.exact_reference_score, ReconciliationMatchReason.EXACT_REFERENCE
        if left in right or right in left:
            return (
                self.policy.reference_contains_score,
                ReconciliationMatchReason.REFERENCE_CONTAINS,
            )
        return Decimal("0"), None

    @staticmethod
    def _normalized_text(value: str | None) -> str:
        if value is None:
            return ""
        return "".join(_TOKEN_PATTERN.findall(value.upper()))
