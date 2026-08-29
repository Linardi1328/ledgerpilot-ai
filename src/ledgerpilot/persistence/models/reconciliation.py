from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ledgerpilot.persistence.base import Base, utc_now
from ledgerpilot.reconciliation.types import (
    BankTransactionDirection,
    ReconciliationCandidateStatus,
)

_DIRECTION_VALUES = ", ".join(f"'{direction.value}'" for direction in BankTransactionDirection)
_MATCH_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in ReconciliationCandidateStatus)


class BankImportBatchRecord(Base):
    __tablename__ = "bank_import_batches"
    __table_args__ = (
        CheckConstraint("length(provider_name) > 0", name="ck_bank_import_batches_provider_name"),
        CheckConstraint(
            "length(provider_version) > 0",
            name="ck_bank_import_batches_provider_version",
        ),
        CheckConstraint(
            "length(provider_batch_reference) > 0",
            name="ck_bank_import_batches_provider_batch_reference",
        ),
        CheckConstraint(
            "length(account_reference) > 0",
            name="ck_bank_import_batches_account_reference",
        ),
        CheckConstraint(
            "period_end >= period_start",
            name="ck_bank_import_batches_period",
        ),
        ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_bank_import_batches_client_firm",
        ),
        UniqueConstraint(
            "firm_id",
            "client_id",
            "provider_name",
            "account_reference",
            "provider_batch_reference",
            name="uq_bank_import_batches_provider_reference",
        ),
        UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "provider_name",
            "account_reference",
            name="uq_bank_import_batches_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("firms.id"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    provider_version: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_batch_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    account_reference: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class BankTransactionRecord(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (
        CheckConstraint(
            f"direction in ({_DIRECTION_VALUES})",
            name="ck_bank_transactions_direction",
        ),
        CheckConstraint("amount > 0", name="ck_bank_transactions_amount_positive"),
        CheckConstraint("length(currency) = 3", name="ck_bank_transactions_currency"),
        CheckConstraint(
            "length(source_transaction_id) > 0",
            name="ck_bank_transactions_source_transaction_id",
        ),
        CheckConstraint("length(description) > 0", name="ck_bank_transactions_description"),
        CheckConstraint("length(provider_name) > 0", name="ck_bank_transactions_provider_name"),
        CheckConstraint(
            "length(account_reference) > 0",
            name="ck_bank_transactions_account_reference",
        ),
        ForeignKeyConstraint(
            [
                "import_batch_id",
                "firm_id",
                "client_id",
                "provider_name",
                "account_reference",
            ],
            [
                "bank_import_batches.id",
                "bank_import_batches.firm_id",
                "bank_import_batches.client_id",
                "bank_import_batches.provider_name",
                "bank_import_batches.account_reference",
            ],
            name="fk_bank_transactions_batch_scope",
        ),
        UniqueConstraint(
            "firm_id",
            "client_id",
            "provider_name",
            "account_reference",
            "source_transaction_id",
            name="uq_bank_transactions_source_identity",
        ),
        UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            name="uq_bank_transactions_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    account_reference: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_transaction_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ReconciliationMatchRunRecord(Base):
    __tablename__ = "reconciliation_match_runs"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_MATCH_STATUS_VALUES})",
            name="ck_reconciliation_match_runs_status",
        ),
        CheckConstraint(
            "length(matcher_name) > 0",
            name="ck_reconciliation_match_runs_matcher_name",
        ),
        CheckConstraint(
            "length(matcher_version) > 0",
            name="ck_reconciliation_match_runs_matcher_version",
        ),
        ForeignKeyConstraint(
            ["bank_transaction_id", "firm_id", "client_id"],
            [
                "bank_transactions.id",
                "bank_transactions.firm_id",
                "bank_transactions.client_id",
            ],
            name="fk_reconciliation_match_runs_transaction_scope",
        ),
        UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "bank_transaction_id",
            name="uq_reconciliation_match_runs_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    matcher_name: Mapped[str] = mapped_column(String(80), nullable=False)
    matcher_version: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ReconciliationCandidateRecord(Base):
    __tablename__ = "reconciliation_candidates"
    __table_args__ = (
        CheckConstraint(
            "score >= 0 and score <= 1",
            name="ck_reconciliation_candidates_score",
        ),
        CheckConstraint(
            f"target_direction in ({_DIRECTION_VALUES})",
            name="ck_reconciliation_candidates_target_direction",
        ),
        CheckConstraint(
            "target_amount > 0",
            name="ck_reconciliation_candidates_target_amount_positive",
        ),
        CheckConstraint(
            "length(target_currency) = 3",
            name="ck_reconciliation_candidates_target_currency",
        ),
        ForeignKeyConstraint(
            ["match_run_id", "firm_id", "client_id", "bank_transaction_id"],
            [
                "reconciliation_match_runs.id",
                "reconciliation_match_runs.firm_id",
                "reconciliation_match_runs.client_id",
                "reconciliation_match_runs.bank_transaction_id",
            ],
            name="fk_reconciliation_candidates_match_run_scope",
        ),
        ForeignKeyConstraint(
            [
                "review_outcome_id",
                "firm_id",
                "client_id",
                "decision_run_id",
                "document_id",
            ],
            [
                "review_outcomes.id",
                "review_outcomes.firm_id",
                "review_outcomes.client_id",
                "review_outcomes.decision_run_id",
                "review_outcomes.document_id",
            ],
            name="fk_reconciliation_candidates_outcome_scope",
        ),
        UniqueConstraint(
            "match_run_id",
            "review_outcome_id",
            name="uq_reconciliation_candidates_run_outcome",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    review_outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    reasons_json: Mapped[list[str]] = mapped_column(
        "reasons",
        JSON,
        nullable=False,
        default=list,
    )
    target_transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
