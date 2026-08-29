from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from ledgerpilot.reconciliation.matching import ReconciliationMatchingPolicy
from ledgerpilot.reconciliation.types import (
    BankTransactionDirection,
    ImportedBankTransaction,
    ReconciliationCandidateStatus,
    ReconciliationMatchResult,
)

FIRM_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CLIENT_ID = UUID("11111111-1111-1111-1111-111111111111")


def transaction(**overrides: object) -> ImportedBankTransaction:
    values: dict[str, object] = {
        "firm_id": FIRM_ID,
        "client_id": CLIENT_ID,
        "source_transaction_id": "txn-validation-001",
        "booking_date": date(2026, 8, 20),
        "direction": BankTransactionDirection.DEBIT,
        "amount": Decimal("10.00"),
        "currency": "MYR",
        "description": "SYNTHETIC VALIDATION TRANSACTION",
    }
    values.update(overrides)
    return ImportedBankTransaction(**values)  # type: ignore[arg-type]


def test_non_finite_money_is_rejected() -> None:
    for invalid_amount in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(ValueError, match="amount must be finite"):
            transaction(amount=invalid_amount)


def test_malformed_runtime_direction_and_currency_are_rejected() -> None:
    with pytest.raises(TypeError, match="BankTransactionDirection"):
        transaction(direction="debit")

    with pytest.raises(ValueError, match="three-letter alphabetic"):
        transaction(currency="M1R")


def test_matching_policy_rejects_non_finite_or_out_of_range_scores() -> None:
    with pytest.raises(ValueError, match="matching scores must be finite"):
        ReconciliationMatchingPolicy(base_exact_match_score=Decimal("NaN"))

    with pytest.raises(ValueError, match="matching scores must be between zero and one"):
        ReconciliationMatchingPolicy(exact_reference_score=Decimal("1.01"))


def test_match_result_requires_matcher_lineage_even_when_unmatched() -> None:
    with pytest.raises(ValueError, match="matcher lineage"):
        ReconciliationMatchResult(
            source_transaction_id="txn-validation-001",
            status=ReconciliationCandidateStatus.UNMATCHED,
            candidates=(),
            matcher_name="",
            matcher_version="1.0",
        )
