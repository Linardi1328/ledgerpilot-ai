from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from ledgerpilot.accounting.types import EffectiveExtractionValue
from ledgerpilot.persistence.models.accounting import ProposedJournal
from ledgerpilot.persistence.models.review import ReviewOutcome
from ledgerpilot.reconciliation.types import (
    ApprovedReconciliationTarget,
    BankTransactionDirection,
)
from ledgerpilot.review.states import ReviewOutcomeType

_APPROVED_OUTCOME_TYPES = frozenset(
    {
        ReviewOutcomeType.APPROVED.value,
        ReviewOutcomeType.CORRECTED_AND_APPROVED.value,
    }
)


def project_approved_reconciliation_target(
    *,
    outcome: ReviewOutcome,
    journal: ProposedJournal | None,
    effective_values: dict[str, EffectiveExtractionValue],
) -> ApprovedReconciliationTarget | None:
    if outcome.outcome_type not in _APPROVED_OUTCOME_TYPES:
        return None
    if outcome.proposed_journal_id is None or journal is None:
        return None
    if journal.id != outcome.proposed_journal_id or not journal.is_balanced:
        return None
    if journal.total_debits != journal.total_credits or journal.total_debits <= Decimal("0"):
        return None

    document_type = _effective_text(effective_values, "document.type")
    if document_type != "purchase_invoice":
        return None

    transaction_date = _effective_date(effective_values, "invoice.date")
    invoice_total = _effective_decimal(effective_values, "invoice.total")
    currency = _effective_text(effective_values, "invoice.currency")
    if transaction_date is None or invoice_total is None or currency is None:
        return None

    normalized_currency = currency.strip().upper()
    if invoice_total != journal.total_debits:
        return None
    if normalized_currency != journal.currency.strip().upper():
        return None

    return ApprovedReconciliationTarget(
        firm_id=outcome.firm_id,
        client_id=outcome.client_id,
        review_outcome_id=outcome.id,
        decision_run_id=outcome.decision_run_id,
        document_id=outcome.document_id,
        transaction_date=transaction_date,
        direction=BankTransactionDirection.DEBIT,
        amount=invoice_total,
        currency=normalized_currency,
        reference=_effective_text(effective_values, "invoice.number"),
        counterparty_name=_effective_text(effective_values, "supplier.name"),
    )


def _effective_text(
    effective_values: dict[str, EffectiveExtractionValue],
    field_path: str,
) -> str | None:
    value = effective_values.get(field_path)
    if value is None:
        return None
    text = value.normalized_value if value.normalized_value is not None else value.raw_value
    normalized = text.strip()
    return normalized or None


def _effective_date(
    effective_values: dict[str, EffectiveExtractionValue],
    field_path: str,
) -> date | None:
    text = _effective_text(effective_values, field_path)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _effective_decimal(
    effective_values: dict[str, EffectiveExtractionValue],
    field_path: str,
) -> Decimal | None:
    text = _effective_text(effective_values, field_path)
    if text is None:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount <= Decimal("0"):
        return None
    return amount
