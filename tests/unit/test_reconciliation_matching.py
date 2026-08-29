from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from ledgerpilot.reconciliation.matching import (
    DeterministicReconciliationMatcher,
    ReconciliationMatchingPolicy,
)
from ledgerpilot.reconciliation.providers import SyntheticBankTransactionProvider
from ledgerpilot.reconciliation.types import (
    ApprovedReconciliationTarget,
    BankImportBatch,
    BankImportRequest,
    BankTransactionDirection,
    ImportedBankTransaction,
    ReconciliationCandidateStatus,
    ReconciliationMatchReason,
)

FIRM_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER_FIRM_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CLIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_CLIENT_ID = UUID("99999999-9999-9999-9999-999999999999")
OUTCOME_1 = UUID("22222222-2222-2222-2222-222222222222")
OUTCOME_2 = UUID("33333333-3333-3333-3333-333333333333")
DECISION_1 = UUID("44444444-4444-4444-4444-444444444444")
DECISION_2 = UUID("55555555-5555-5555-5555-555555555555")
DOCUMENT_1 = UUID("66666666-6666-6666-6666-666666666666")
DOCUMENT_2 = UUID("77777777-7777-7777-7777-777777777777")


def bank_transaction(**overrides: object) -> ImportedBankTransaction:
    values: dict[str, object] = {
        "firm_id": FIRM_ID,
        "client_id": CLIENT_ID,
        "source_transaction_id": "txn-001",
        "booking_date": date(2026, 8, 20),
        "direction": BankTransactionDirection.DEBIT,
        "amount": Decimal("1250.40"),
        "currency": "MYR",
        "description": "SYNTHETIC SUPPLIER PAYMENT",
        "reference": "INV-SYN-1001",
        "counterparty_name": "Synthetic Office Supply Sdn Bhd",
    }
    values.update(overrides)
    return ImportedBankTransaction(**values)  # type: ignore[arg-type]


def target(
    *,
    outcome_id: UUID = OUTCOME_1,
    decision_id: UUID = DECISION_1,
    document_id: UUID = DOCUMENT_1,
    **overrides: object,
) -> ApprovedReconciliationTarget:
    values: dict[str, object] = {
        "firm_id": FIRM_ID,
        "client_id": CLIENT_ID,
        "review_outcome_id": outcome_id,
        "decision_run_id": decision_id,
        "document_id": document_id,
        "transaction_date": date(2026, 8, 20),
        "direction": BankTransactionDirection.DEBIT,
        "amount": Decimal("1250.40"),
        "currency": "MYR",
        "reference": "INV-SYN-1001",
        "counterparty_name": "Synthetic Office Supply Sdn Bhd",
    }
    values.update(overrides)
    return ApprovedReconciliationTarget(**values)  # type: ignore[arg-type]


def test_exact_match_produces_candidate_but_never_auto_reconciles() -> None:
    result = DeterministicReconciliationMatcher().match(bank_transaction(), (target(),))

    assert result.status is ReconciliationCandidateStatus.CANDIDATES_AVAILABLE
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.target.review_outcome_id == OUTCOME_1
    assert candidate.score == Decimal("1")
    assert ReconciliationMatchReason.EXACT_AMOUNT in candidate.reasons
    assert ReconciliationMatchReason.EXACT_REFERENCE in candidate.reasons
    assert candidate.matcher_name == "deterministic_exact_bank_matcher"


def test_amount_currency_and_direction_are_hard_gates() -> None:
    matcher = DeterministicReconciliationMatcher()

    for candidate_target in (
        target(amount=Decimal("1250.41")),
        target(currency="USD"),
        target(direction=BankTransactionDirection.CREDIT),
    ):
        result = matcher.match(bank_transaction(), (candidate_target,))
        assert result.status is ReconciliationCandidateStatus.UNMATCHED
        assert result.candidates == ()


def test_cross_tenant_targets_are_never_candidates() -> None:
    matcher = DeterministicReconciliationMatcher()

    for candidate_target in (
        target(client_id=OTHER_CLIENT_ID),
        target(firm_id=OTHER_FIRM_ID),
    ):
        result = matcher.match(bank_transaction(), (candidate_target,))
        assert result.status is ReconciliationCandidateStatus.UNMATCHED
        assert result.candidates == ()


def test_date_outside_window_is_not_candidate() -> None:
    result = DeterministicReconciliationMatcher().match(
        bank_transaction(),
        (target(transaction_date=date(2026, 8, 10)),),
    )

    assert result.status is ReconciliationCandidateStatus.UNMATCHED


def test_near_date_stays_reviewable_and_retains_reason() -> None:
    result = DeterministicReconciliationMatcher().match(
        bank_transaction(),
        (target(transaction_date=date(2026, 8, 18)),),
    )

    assert result.status is ReconciliationCandidateStatus.CANDIDATES_AVAILABLE
    assert ReconciliationMatchReason.NEAR_DATE in result.candidates[0].reasons
    assert result.candidates[0].score == Decimal("0.88")


def test_candidate_order_is_deterministic_on_score_tie() -> None:
    first = target(outcome_id=OUTCOME_2, decision_id=DECISION_2, document_id=DOCUMENT_2)
    second = target(outcome_id=OUTCOME_1)

    result = DeterministicReconciliationMatcher().match(bank_transaction(), (first, second))

    assert [candidate.target.review_outcome_id for candidate in result.candidates] == [
        OUTCOME_1,
        OUTCOME_2,
    ]


def test_reference_normalization_is_deterministic() -> None:
    result = DeterministicReconciliationMatcher().match(
        bank_transaction(reference=" inv syn 1001 "),
        (target(reference="INV-SYN-1001"),),
    )

    assert ReconciliationMatchReason.EXACT_REFERENCE in result.candidates[0].reasons


def test_policy_threshold_can_keep_weak_candidate_unmatched() -> None:
    policy = ReconciliationMatchingPolicy(minimum_candidate_score=Decimal("0.90"))
    result = DeterministicReconciliationMatcher(policy).match(
        bank_transaction(reference=None, counterparty_name=None),
        (target(reference=None, counterparty_name=None, transaction_date=date(2026, 8, 19)),),
    )

    assert result.status is ReconciliationCandidateStatus.UNMATCHED


def test_binary_float_money_is_rejected() -> None:
    with pytest.raises(TypeError, match="binary floating point"):
        bank_transaction(amount=1250.40)

    with pytest.raises(TypeError, match="binary floating point"):
        target(amount=1250.40)


def test_import_batch_rejects_duplicate_provider_transaction_ids() -> None:
    transaction = bank_transaction()

    with pytest.raises(ValueError, match="duplicate source_transaction_id"):
        BankImportBatch(
            firm_id=FIRM_ID,
            client_id=CLIENT_ID,
            provider_name="synthetic_bank_feed",
            provider_version="1.0",
            provider_batch_reference="batch-001",
            account_reference="SYN-BANK-001",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            transactions=(transaction, transaction),
        )


def test_synthetic_provider_returns_only_exact_requested_batch() -> None:
    batch = BankImportBatch(
        firm_id=FIRM_ID,
        client_id=CLIENT_ID,
        provider_name="synthetic_bank_feed",
        provider_version="1.0",
        provider_batch_reference="batch-001",
        account_reference="SYN-BANK-001",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        transactions=(bank_transaction(),),
    )
    provider = SyntheticBankTransactionProvider((batch,))

    result = provider.fetch_transactions(
        BankImportRequest(
            firm_id=FIRM_ID,
            client_id=CLIENT_ID,
            account_reference="SYN-BANK-001",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
        )
    )

    assert result is batch


def test_import_request_rejects_invalid_period() -> None:
    with pytest.raises(ValueError, match="period_end"):
        BankImportRequest(
            firm_id=FIRM_ID,
            client_id=CLIENT_ID,
            account_reference="SYN-BANK-001",
            period_start=date(2026, 9, 1),
            period_end=date(2026, 8, 31),
        )
