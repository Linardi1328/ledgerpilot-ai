from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ledgerpilot.accounting.states import AccountingDecisionRunStatus
from ledgerpilot.accounting.types import (
    AccountingDecisionFailureCode,
    AccountingFindingCode,
    AccountingFindingSeverity,
    AccountingRecommendationType,
    JournalBalanceStatus,
)
from ledgerpilot.persistence.base import Base, utc_now

_DECISION_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in AccountingDecisionRunStatus)
_DECISION_FAILURE_VALUES = ", ".join(f"'{code.value}'" for code in AccountingDecisionFailureCode)
_FINDING_CODE_VALUES = ", ".join(f"'{code.value}'" for code in AccountingFindingCode)
_FINDING_SEVERITY_VALUES = ", ".join(
    f"'{severity.value}'" for severity in AccountingFindingSeverity
)
_RECOMMENDATION_TYPE_VALUES = ", ".join(
    f"'{recommendation_type.value}'" for recommendation_type in AccountingRecommendationType
)
_JOURNAL_BALANCE_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in JournalBalanceStatus)


def _decision_run_scope_fk(name: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["decision_run_id", "firm_id", "client_id", "document_id", "extraction_run_id"],
        [
            "accounting_decision_runs.id",
            "accounting_decision_runs.firm_id",
            "accounting_decision_runs.client_id",
            "accounting_decision_runs.document_id",
            "accounting_decision_runs.extraction_run_id",
        ],
        name=name,
    )


class AccountingDecisionRun(Base):
    __tablename__ = "accounting_decision_runs"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_DECISION_STATUS_VALUES})",
            name="ck_accounting_decision_runs_status",
        ),
        CheckConstraint(
            f"failure_code is null or failure_code in ({_DECISION_FAILURE_VALUES})",
            name="ck_accounting_decision_runs_failure_code",
        ),
        CheckConstraint(
            "length(engine_name) > 0",
            name="ck_accounting_decision_runs_engine_name",
        ),
        CheckConstraint(
            "length(engine_version) > 0",
            name="ck_accounting_decision_runs_engine_version",
        ),
        CheckConstraint(
            "length(source_sha256) = 64",
            name="ck_accounting_decision_runs_source_sha256",
        ),
        ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_accounting_decision_runs_client_firm",
        ),
        ForeignKeyConstraint(
            ["document_id", "firm_id", "client_id"],
            ["documents.id", "documents.firm_id", "documents.client_id"],
            name="fk_accounting_decision_runs_document_scope",
        ),
        ForeignKeyConstraint(
            ["extraction_run_id", "firm_id", "client_id", "document_id"],
            [
                "extraction_runs.id",
                "extraction_runs.firm_id",
                "extraction_runs.client_id",
                "extraction_runs.document_id",
            ],
            name="fk_accounting_decision_runs_extraction_scope",
        ),
        ForeignKeyConstraint(
            ["initiated_by_membership_id", "initiated_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_accounting_decision_runs_initiator_membership_user_firm",
        ),
        UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "document_id",
            "extraction_run_id",
            name="uq_accounting_decision_runs_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("firms.id"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    initiated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    initiated_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    engine_name: Mapped[str] = mapped_column(String(80), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class AccountingDecisionFinding(Base):
    __tablename__ = "accounting_decision_findings"
    __table_args__ = (
        CheckConstraint(
            f"code in ({_FINDING_CODE_VALUES})",
            name="ck_accounting_decision_findings_code",
        ),
        CheckConstraint(
            f"severity in ({_FINDING_SEVERITY_VALUES})",
            name="ck_accounting_decision_findings_severity",
        ),
        CheckConstraint(
            "field_path is null or length(field_path) > 0",
            name="ck_accounting_decision_findings_field_path",
        ),
        CheckConstraint(
            "length(description) > 0",
            name="ck_accounting_decision_findings_description",
        ),
        _decision_run_scope_fk("fk_accounting_decision_findings_run_scope"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    field_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(
        "evidence",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class AccountingSupplierMatchCandidate(Base):
    __tablename__ = "accounting_supplier_match_candidates"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_accounting_supplier_match_candidates_confidence",
        ),
        CheckConstraint(
            "length(supplier_reference) > 0",
            name="ck_accounting_supplier_match_candidates_reference",
        ),
        CheckConstraint(
            "length(supplier_name) > 0",
            name="ck_accounting_supplier_match_candidates_name",
        ),
        CheckConstraint(
            "length(explanation) > 0",
            name="ck_accounting_supplier_match_candidates_explanation",
        ),
        CheckConstraint(
            "length(matcher_name) > 0",
            name="ck_accounting_supplier_match_candidates_matcher_name",
        ),
        CheckConstraint(
            "length(matcher_version) > 0",
            name="ck_accounting_supplier_match_candidates_matcher_version",
        ),
        _decision_run_scope_fk("fk_accounting_supplier_match_candidates_run_scope"),
        UniqueConstraint(
            "decision_run_id",
            "supplier_reference",
            name="uq_accounting_supplier_match_candidates_run_supplier",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    supplier_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(
        "evidence",
        JSON,
        nullable=False,
        default=dict,
    )
    matcher_name: Mapped[str] = mapped_column(String(80), nullable=False)
    matcher_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_confident: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class AccountingDuplicateCandidate(Base):
    __tablename__ = "accounting_duplicate_candidates"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_accounting_duplicate_candidates_confidence",
        ),
        CheckConstraint(
            "length(explanation) > 0",
            name="ck_accounting_duplicate_candidates_explanation",
        ),
        CheckConstraint(
            "length(detector_name) > 0",
            name="ck_accounting_duplicate_candidates_detector_name",
        ),
        CheckConstraint(
            "length(detector_version) > 0",
            name="ck_accounting_duplicate_candidates_detector_version",
        ),
        _decision_run_scope_fk("fk_accounting_duplicate_candidates_run_scope"),
        ForeignKeyConstraint(
            ["candidate_document_id", "firm_id", "client_id"],
            ["documents.id", "documents.firm_id", "documents.client_id"],
            name="fk_accounting_duplicate_candidates_document_scope",
        ),
        ForeignKeyConstraint(
            ["candidate_extraction_run_id", "firm_id", "client_id", "candidate_document_id"],
            [
                "extraction_runs.id",
                "extraction_runs.firm_id",
                "extraction_runs.client_id",
                "extraction_runs.document_id",
            ],
            name="fk_accounting_duplicate_candidates_extraction_scope",
        ),
        ForeignKeyConstraint(
            [
                "candidate_decision_run_id",
                "firm_id",
                "client_id",
                "candidate_document_id",
                "candidate_extraction_run_id",
            ],
            [
                "accounting_decision_runs.id",
                "accounting_decision_runs.firm_id",
                "accounting_decision_runs.client_id",
                "accounting_decision_runs.document_id",
                "accounting_decision_runs.extraction_run_id",
            ],
            name="fk_accounting_duplicate_candidates_decision_scope",
        ),
        UniqueConstraint(
            "decision_run_id",
            "candidate_decision_run_id",
            name="uq_accounting_duplicate_candidates_run_candidate",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    candidate_document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    candidate_extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    candidate_decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(
        "evidence",
        JSON,
        nullable=False,
        default=dict,
    )
    detector_name: Mapped[str] = mapped_column(String(80), nullable=False)
    detector_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class AccountingRecommendation(Base):
    __tablename__ = "accounting_recommendations"
    __table_args__ = (
        CheckConstraint(
            f"recommendation_type in ({_RECOMMENDATION_TYPE_VALUES})",
            name="ck_accounting_recommendations_type",
        ),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_accounting_recommendations_confidence",
        ),
        CheckConstraint(
            "length(recommended_value) > 0",
            name="ck_accounting_recommendations_value",
        ),
        CheckConstraint(
            "length(explanation) > 0",
            name="ck_accounting_recommendations_explanation",
        ),
        CheckConstraint(
            "length(rule_name) > 0",
            name="ck_accounting_recommendations_rule_name",
        ),
        CheckConstraint(
            "length(rule_version) > 0",
            name="ck_accounting_recommendations_rule_version",
        ),
        _decision_run_scope_fk("fk_accounting_recommendations_run_scope"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    recommendation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    recommended_value: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(
        "evidence",
        JSON,
        nullable=False,
        default=dict,
    )
    rule_name: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ProposedJournal(Base):
    __tablename__ = "proposed_journals"
    __table_args__ = (
        CheckConstraint("length(currency) > 0", name="ck_proposed_journals_currency"),
        CheckConstraint("total_debits >= 0", name="ck_proposed_journals_debits_nonnegative"),
        CheckConstraint("total_credits >= 0", name="ck_proposed_journals_credits_nonnegative"),
        CheckConstraint(
            f"balance_status in ({_JOURNAL_BALANCE_STATUS_VALUES})",
            name="ck_proposed_journals_balance_status",
        ),
        CheckConstraint(
            "(total_debits = total_credits and is_balanced = true "
            "and balance_status = 'balanced') "
            "or (total_debits <> total_credits and is_balanced = false "
            "and balance_status = 'unbalanced')",
            name="ck_proposed_journals_balance_consistency",
        ),
        CheckConstraint(
            "length(explanation) > 0",
            name="ck_proposed_journals_explanation",
        ),
        _decision_run_scope_fk("fk_proposed_journals_run_scope"),
        UniqueConstraint("decision_run_id", name="uq_proposed_journals_decision_run"),
        UniqueConstraint(
            "id",
            "decision_run_id",
            "firm_id",
            "client_id",
            "document_id",
            "extraction_run_id",
            name="uq_proposed_journals_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_debits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    balance_status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_balanced: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ProposedJournalLine(Base):
    __tablename__ = "proposed_journal_lines"
    __table_args__ = (
        CheckConstraint("line_number >= 1", name="ck_proposed_journal_lines_line_number"),
        CheckConstraint("length(account_reference) > 0", name="ck_proposed_journal_lines_account"),
        CheckConstraint("debit_amount >= 0", name="ck_proposed_journal_lines_debit_nonnegative"),
        CheckConstraint("credit_amount >= 0", name="ck_proposed_journal_lines_credit_nonnegative"),
        CheckConstraint(
            "((debit_amount > 0 and credit_amount = 0) "
            "or (credit_amount > 0 and debit_amount = 0))",
            name="ck_proposed_journal_lines_single_sided_amount",
        ),
        CheckConstraint(
            "length(explanation) > 0",
            name="ck_proposed_journal_lines_explanation",
        ),
        ForeignKeyConstraint(
            [
                "proposed_journal_id",
                "decision_run_id",
                "firm_id",
                "client_id",
                "document_id",
                "extraction_run_id",
            ],
            [
                "proposed_journals.id",
                "proposed_journals.decision_run_id",
                "proposed_journals.firm_id",
                "proposed_journals.client_id",
                "proposed_journals.document_id",
                "proposed_journals.extraction_run_id",
            ],
            name="fk_proposed_journal_lines_journal_scope",
        ),
        UniqueConstraint(
            "proposed_journal_id",
            "line_number",
            name="uq_proposed_journal_lines_journal_line",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposed_journal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    decision_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_code_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cost_centre_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)
    lineage_json: Mapped[dict[str, Any]] = mapped_column(
        "lineage",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
