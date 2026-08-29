from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class BankTransactionDirection(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class ReconciliationCandidateStatus(StrEnum):
    UNMATCHED = "unmatched"
    CANDIDATES_AVAILABLE = "candidates_available"


class ReconciliationMatchReason(StrEnum):
    EXACT_AMOUNT = "exact_amount"
    EXACT_CURRENCY = "exact_currency"
    EXACT_DIRECTION = "exact_direction"
    SAME_DATE = "same_date"
    NEAR_DATE = "near_date"
    EXACT_REFERENCE = "exact_reference"
    REFERENCE_CONTAINS = "reference_contains"
    EXACT_COUNTERPARTY = "exact_counterparty"


def _validate_uuid(value: UUID, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise TypeError(f"{field_name} must be UUID")


def _validate_money(amount: Decimal) -> None:
    if not isinstance(amount, Decimal):
        raise TypeError("amount must be Decimal; binary floating point is not permitted")
    if not amount.is_finite():
        raise ValueError("amount must be finite")
    if amount <= Decimal("0"):
        raise ValueError("amount must be greater than zero")


def _validate_currency(currency: str) -> None:
    normalized = currency.strip()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("currency must be a three-letter alphabetic code")


def _validate_direction(direction: BankTransactionDirection) -> None:
    if not isinstance(direction, BankTransactionDirection):
        raise TypeError("direction must be BankTransactionDirection")


@dataclass(frozen=True)
class BankImportRequest:
    firm_id: UUID
    client_id: UUID
    account_reference: str
    period_start: date
    period_end: date

    def __post_init__(self) -> None:
        _validate_uuid(self.firm_id, "firm_id")
        _validate_uuid(self.client_id, "client_id")
        if not self.account_reference.strip():
            raise ValueError("account_reference must not be blank")
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")


@dataclass(frozen=True)
class ImportedBankTransaction:
    firm_id: UUID
    client_id: UUID
    source_transaction_id: str
    booking_date: date
    direction: BankTransactionDirection
    amount: Decimal
    currency: str
    description: str
    reference: str | None = None
    counterparty_name: str | None = None
    value_date: date | None = None

    def __post_init__(self) -> None:
        _validate_uuid(self.firm_id, "firm_id")
        _validate_uuid(self.client_id, "client_id")
        _validate_direction(self.direction)
        _validate_money(self.amount)
        _validate_currency(self.currency)
        if not self.source_transaction_id.strip():
            raise ValueError("source_transaction_id must not be blank")
        if not self.description.strip():
            raise ValueError("description must not be blank")

    @property
    def normalized_currency(self) -> str:
        return self.currency.strip().upper()


@dataclass(frozen=True)
class BankImportBatch:
    firm_id: UUID
    client_id: UUID
    provider_name: str
    provider_version: str
    provider_batch_reference: str
    account_reference: str
    period_start: date
    period_end: date
    transactions: tuple[ImportedBankTransaction, ...]

    def __post_init__(self) -> None:
        _validate_uuid(self.firm_id, "firm_id")
        _validate_uuid(self.client_id, "client_id")
        if not self.provider_name.strip():
            raise ValueError("provider_name must not be blank")
        if not self.provider_version.strip():
            raise ValueError("provider_version must not be blank")
        if not self.provider_batch_reference.strip():
            raise ValueError("provider_batch_reference must not be blank")
        if not self.account_reference.strip():
            raise ValueError("account_reference must not be blank")
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        seen_source_ids: set[str] = set()
        for transaction in self.transactions:
            if transaction.firm_id != self.firm_id or transaction.client_id != self.client_id:
                raise ValueError("transaction ownership must match import batch")
            if transaction.source_transaction_id in seen_source_ids:
                raise ValueError("duplicate source_transaction_id in import batch")
            seen_source_ids.add(transaction.source_transaction_id)
            if not self.period_start <= transaction.booking_date <= self.period_end:
                raise ValueError("transaction booking_date must fall within import period")


@dataclass(frozen=True)
class ApprovedReconciliationTarget:
    firm_id: UUID
    client_id: UUID
    review_outcome_id: UUID
    decision_run_id: UUID
    document_id: UUID
    transaction_date: date
    direction: BankTransactionDirection
    amount: Decimal
    currency: str
    reference: str | None = None
    counterparty_name: str | None = None

    def __post_init__(self) -> None:
        _validate_uuid(self.firm_id, "firm_id")
        _validate_uuid(self.client_id, "client_id")
        _validate_uuid(self.review_outcome_id, "review_outcome_id")
        _validate_uuid(self.decision_run_id, "decision_run_id")
        _validate_uuid(self.document_id, "document_id")
        _validate_direction(self.direction)
        _validate_money(self.amount)
        _validate_currency(self.currency)

    @property
    def normalized_currency(self) -> str:
        return self.currency.strip().upper()


@dataclass(frozen=True)
class ReconciliationCandidateDecision:
    target: ApprovedReconciliationTarget
    score: Decimal
    reasons: tuple[ReconciliationMatchReason, ...]
    matcher_name: str
    matcher_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.score, Decimal):
            raise TypeError("score must be Decimal")
        if not self.score.is_finite():
            raise ValueError("score must be finite")
        if not Decimal("0") <= self.score <= Decimal("1"):
            raise ValueError("score must be between zero and one")
        if not self.reasons:
            raise ValueError("candidate must retain at least one match reason")
        if not self.matcher_name.strip() or not self.matcher_version.strip():
            raise ValueError("candidate matcher lineage must not be blank")


@dataclass(frozen=True)
class ReconciliationMatchResult:
    source_transaction_id: str
    status: ReconciliationCandidateStatus
    candidates: tuple[ReconciliationCandidateDecision, ...]

    def __post_init__(self) -> None:
        if not self.source_transaction_id.strip():
            raise ValueError("source_transaction_id must not be blank")
        if not isinstance(self.status, ReconciliationCandidateStatus):
            raise TypeError("status must be ReconciliationCandidateStatus")
        if self.status is ReconciliationCandidateStatus.UNMATCHED and self.candidates:
            raise ValueError("unmatched result cannot contain candidates")
        if (
            self.status is ReconciliationCandidateStatus.CANDIDATES_AVAILABLE
            and not self.candidates
        ):
            raise ValueError("candidates_available result requires candidates")
