from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AccountingDecisionFailureCode(StrEnum):
    SOURCE_NOT_ELIGIBLE = "source_not_eligible"
    DECISION_ENGINE_FAILED = "decision_engine_failed"
    PERSISTENCE_FAILED = "persistence_failed"


class AccountingFindingCode(StrEnum):
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNSUPPORTED_DOCUMENT_TYPE = "unsupported_document_type"
    INVALID_MONETARY_VALUE = "invalid_monetary_value"
    INVALID_CURRENCY = "invalid_currency"
    ARITHMETIC_MISMATCH = "arithmetic_mismatch"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    NEW_SUPPLIER = "new_supplier"
    LOW_EXTRACTION_CONFIDENCE = "low_extraction_confidence"
    UNKNOWN_ACCOUNT_MAPPING = "unknown_account_mapping"
    TAX_REVIEW_REQUIRED = "tax_review_required"
    UNBALANCED_JOURNAL = "unbalanced_journal"


class AccountingFindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SupplierMatchStatus(StrEnum):
    CONFIDENT_MATCH = "confident_match"
    CANDIDATE_MATCHES = "candidate_matches"
    NO_MATCH = "no_match"


class AccountingRecommendationType(StrEnum):
    GL_ACCOUNT = "gl_account"
    TAX_CODE = "tax_code"
    COST_CENTRE = "cost_centre"
    CATEGORY = "category"


class JournalBalanceStatus(StrEnum):
    BALANCED = "balanced"
    UNBALANCED = "unbalanced"


@dataclass(frozen=True)
class EffectiveExtractionValue:
    field_id: UUID
    field_path: str
    value_type: str
    raw_value: str
    normalized_value: str | None
    confidence: Decimal | None
    source_page_number: int | None
    corrected: bool
    latest_correction_id: UUID | None
    latest_revision_number: int | None

    @property
    def value(self) -> str:
        return self.normalized_value if self.normalized_value is not None else self.raw_value


@dataclass(frozen=True)
class AccountingFindingDecision:
    code: AccountingFindingCode
    severity: AccountingFindingSeverity
    description: str
    field_path: str | None = None
    evidence: dict[str, object] | None = None


@dataclass(frozen=True)
class SupplierMatchCandidateDecision:
    supplier_reference: str
    supplier_name: str
    confidence: Decimal
    explanation: str
    evidence: dict[str, object]
    matcher_name: str
    matcher_version: str
    model_version: str | None
    is_confident: bool


@dataclass(frozen=True)
class SupplierMatchDecision:
    status: SupplierMatchStatus
    candidates: tuple[SupplierMatchCandidateDecision, ...]


@dataclass(frozen=True)
class DuplicateCandidateDecision:
    candidate_document_id: UUID
    candidate_extraction_run_id: UUID
    candidate_decision_run_id: UUID
    confidence: Decimal
    explanation: str
    evidence: dict[str, object]
    detector_name: str
    detector_version: str
    model_version: str | None


@dataclass(frozen=True)
class AccountingRecommendationDecision:
    recommendation_type: AccountingRecommendationType
    recommended_value: str
    confidence: Decimal | None
    explanation: str
    evidence: dict[str, object]
    rule_name: str
    rule_version: str
    model_version: str | None


@dataclass(frozen=True)
class ProposedJournalLineDecision:
    line_number: int
    account_reference: str
    debit_amount: Decimal
    credit_amount: Decimal
    tax_code_reference: str | None
    cost_centre_reference: str | None
    explanation: str
    lineage: dict[str, object]


@dataclass(frozen=True)
class ProposedJournalDecision:
    currency: str
    total_debits: Decimal
    total_credits: Decimal
    balance_status: JournalBalanceStatus
    is_balanced: bool
    explanation: str
    lines: tuple[ProposedJournalLineDecision, ...]


@dataclass(frozen=True)
class PriorDecisionSnapshot:
    decision_run_id: UUID
    document_id: UUID
    extraction_run_id: UUID
    source_sha256: str
    effective_values: dict[str, EffectiveExtractionValue]


@dataclass(frozen=True)
class AccountingDecisionOutput:
    findings: tuple[AccountingFindingDecision, ...]
    supplier_match: SupplierMatchDecision
    duplicate_candidates: tuple[DuplicateCandidateDecision, ...]
    recommendations: tuple[AccountingRecommendationDecision, ...]
    proposed_journal: ProposedJournalDecision | None
