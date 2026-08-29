from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from ledgerpilot.persistence.models.reconciliation import (
    BankImportBatchRecord,
    BankTransactionRecord,
    ReconciliationCandidateRecord,
    ReconciliationMatchRunRecord,
)
from ledgerpilot.reconciliation.types import (
    BankImportBatch,
    BankTransactionDirection,
    ImportedBankTransaction,
)

_MAX_MONEY = Decimal("99999999999999.9999")
_MONEY_QUANTUM = Decimal("0.0001")


class SyntheticBankTransactionCreateRequest(BaseModel):
    source_transaction_id: str = Field(min_length=1, max_length=200)
    booking_date: date
    value_date: date | None = None
    direction: BankTransactionDirection
    amount: str = Field(min_length=1, max_length=40)
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(min_length=1, max_length=500)
    reference: str | None = Field(default=None, max_length=255)
    counterparty_name: str | None = Field(default=None, max_length=255)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str) -> str:
        try:
            amount = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError("amount must be a decimal string") from exc
        if not amount.is_finite() or amount <= Decimal("0"):
            raise ValueError("amount must be a positive finite decimal")
        if abs(amount) > _MAX_MONEY:
            raise ValueError("amount exceeds supported precision")
        if amount.quantize(_MONEY_QUANTUM) != amount:
            raise ValueError("amount supports at most four decimal places")
        return value.strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code")
        return normalized


class SyntheticBankImportCreateRequest(BaseModel):
    provider_batch_reference: str = Field(min_length=1, max_length=160)
    account_reference: str = Field(min_length=1, max_length=160)
    period_start: date
    period_end: date
    transactions: list[SyntheticBankTransactionCreateRequest] = Field(min_length=1, max_length=5000)

    @field_validator("period_end")
    @classmethod
    def validate_period_end(cls, value: date, info: ValidationInfo) -> date:
        period_start = info.data.get("period_start")
        if isinstance(period_start, date) and value < period_start:
            raise ValueError("period_end must be on or after period_start")
        return value

    def to_batch(
        self,
        *,
        firm_id: UUID,
        client_id: UUID,
        provider_name: str,
        provider_version: str,
    ) -> BankImportBatch:
        transactions = tuple(
            ImportedBankTransaction(
                firm_id=firm_id,
                client_id=client_id,
                source_transaction_id=item.source_transaction_id,
                booking_date=item.booking_date,
                value_date=item.value_date,
                direction=item.direction,
                amount=Decimal(item.amount),
                currency=item.currency,
                description=item.description,
                reference=item.reference,
                counterparty_name=item.counterparty_name,
            )
            for item in self.transactions
        )
        return BankImportBatch(
            firm_id=firm_id,
            client_id=client_id,
            provider_name=provider_name,
            provider_version=provider_version,
            provider_batch_reference=self.provider_batch_reference,
            account_reference=self.account_reference,
            period_start=self.period_start,
            period_end=self.period_end,
            transactions=transactions,
        )


class BankTransactionResponse(BaseModel):
    id: UUID
    import_batch_id: UUID
    source_transaction_id: str
    booking_date: date
    value_date: date | None
    direction: str
    amount: str
    currency: str
    description: str
    reference: str | None
    counterparty_name: str | None
    created_at: datetime

    @classmethod
    def from_record(cls, record: BankTransactionRecord) -> BankTransactionResponse:
        return cls(
            id=record.id,
            import_batch_id=record.import_batch_id,
            source_transaction_id=record.source_transaction_id,
            booking_date=record.booking_date,
            value_date=record.value_date,
            direction=record.direction,
            amount=format(Decimal(record.amount), "f"),
            currency=record.currency,
            description=record.description,
            reference=record.reference,
            counterparty_name=record.counterparty_name,
            created_at=record.created_at,
        )


class BankImportBatchResponse(BaseModel):
    id: UUID
    provider_name: str
    provider_version: str
    provider_batch_reference: str
    account_reference: str
    period_start: date
    period_end: date
    created_at: datetime

    @classmethod
    def from_record(cls, record: BankImportBatchRecord) -> BankImportBatchResponse:
        return cls(
            id=record.id,
            provider_name=record.provider_name,
            provider_version=record.provider_version,
            provider_batch_reference=record.provider_batch_reference,
            account_reference=record.account_reference,
            period_start=record.period_start,
            period_end=record.period_end,
            created_at=record.created_at,
        )


class BankImportResponse(BaseModel):
    created: bool
    batch: BankImportBatchResponse
    transactions: list[BankTransactionResponse]


class ReconciliationMatchRunResponse(BaseModel):
    id: UUID
    bank_transaction_id: UUID
    status: str
    matcher_name: str
    matcher_version: str
    created_at: datetime

    @classmethod
    def from_record(cls, record: ReconciliationMatchRunRecord) -> ReconciliationMatchRunResponse:
        return cls(
            id=record.id,
            bank_transaction_id=record.bank_transaction_id,
            status=record.status,
            matcher_name=record.matcher_name,
            matcher_version=record.matcher_version,
            created_at=record.created_at,
        )


class ReconciliationCandidateResponse(BaseModel):
    id: UUID
    match_run_id: UUID
    bank_transaction_id: UUID
    review_outcome_id: UUID
    decision_run_id: UUID
    document_id: UUID
    score: str
    reasons: list[str]
    target_transaction_date: date
    target_direction: str
    target_amount: str
    target_currency: str
    target_reference: str | None
    target_counterparty_name: str | None
    created_at: datetime

    @classmethod
    def from_record(
        cls,
        record: ReconciliationCandidateRecord,
    ) -> ReconciliationCandidateResponse:
        return cls(
            id=record.id,
            match_run_id=record.match_run_id,
            bank_transaction_id=record.bank_transaction_id,
            review_outcome_id=record.review_outcome_id,
            decision_run_id=record.decision_run_id,
            document_id=record.document_id,
            score=format(Decimal(record.score), "f"),
            reasons=list(record.reasons_json),
            target_transaction_date=record.target_transaction_date,
            target_direction=record.target_direction,
            target_amount=format(Decimal(record.target_amount), "f"),
            target_currency=record.target_currency,
            target_reference=record.target_reference,
            target_counterparty_name=record.target_counterparty_name,
            created_at=record.created_at,
        )


class ReconciliationMatchResponse(BaseModel):
    run: ReconciliationMatchRunResponse
    candidates: list[ReconciliationCandidateResponse]
