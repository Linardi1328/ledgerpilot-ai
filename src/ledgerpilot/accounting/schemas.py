from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from ledgerpilot.accounting.service import AccountingDecisionRunBundle
from ledgerpilot.accounting.types import SupplierMatchStatus
from ledgerpilot.persistence.models.accounting import (
    AccountingDecisionFinding,
    AccountingDecisionRun,
    AccountingDuplicateCandidate,
    AccountingRecommendation,
    AccountingSupplierMatchCandidate,
    ProposedJournal,
    ProposedJournalLine,
)


class AccountingDecisionFindingResponse(BaseModel):
    id: UUID
    code: str
    severity: str
    field_path: str | None
    description: str
    evidence: dict[str, Any]

    @classmethod
    def from_finding(
        cls,
        finding: AccountingDecisionFinding,
    ) -> AccountingDecisionFindingResponse:
        return cls(
            id=finding.id,
            code=finding.code,
            severity=finding.severity,
            field_path=finding.field_path,
            description=finding.description,
            evidence=finding.evidence_json,
        )


class SupplierMatchCandidateResponse(BaseModel):
    id: UUID
    supplier_reference: str
    supplier_name: str
    confidence: str
    explanation: str
    evidence: dict[str, Any]
    matcher_name: str
    matcher_version: str
    model_version: str | None
    is_confident: bool

    @classmethod
    def from_candidate(
        cls,
        candidate: AccountingSupplierMatchCandidate,
    ) -> SupplierMatchCandidateResponse:
        return cls(
            id=candidate.id,
            supplier_reference=candidate.supplier_reference,
            supplier_name=candidate.supplier_name,
            confidence=_required_decimal_to_string(candidate.confidence),
            explanation=candidate.explanation,
            evidence=candidate.evidence_json,
            matcher_name=candidate.matcher_name,
            matcher_version=candidate.matcher_version,
            model_version=candidate.model_version,
            is_confident=candidate.is_confident,
        )


class SupplierMatchResponse(BaseModel):
    status: str
    candidates: list[SupplierMatchCandidateResponse]

    @classmethod
    def from_candidates(
        cls,
        candidates: list[AccountingSupplierMatchCandidate],
    ) -> SupplierMatchResponse:
        if any(candidate.is_confident for candidate in candidates):
            status = SupplierMatchStatus.CONFIDENT_MATCH.value
        elif candidates:
            status = SupplierMatchStatus.CANDIDATE_MATCHES.value
        else:
            status = SupplierMatchStatus.NO_MATCH.value
        return cls(
            status=status,
            candidates=[
                SupplierMatchCandidateResponse.from_candidate(candidate) for candidate in candidates
            ],
        )


class DuplicateCandidateResponse(BaseModel):
    id: UUID
    candidate_document_id: UUID
    candidate_extraction_run_id: UUID
    candidate_decision_run_id: UUID
    confidence: str
    explanation: str
    evidence: dict[str, Any]
    detector_name: str
    detector_version: str
    model_version: str | None

    @classmethod
    def from_candidate(
        cls,
        candidate: AccountingDuplicateCandidate,
    ) -> DuplicateCandidateResponse:
        return cls(
            id=candidate.id,
            candidate_document_id=candidate.candidate_document_id,
            candidate_extraction_run_id=candidate.candidate_extraction_run_id,
            candidate_decision_run_id=candidate.candidate_decision_run_id,
            confidence=_required_decimal_to_string(candidate.confidence),
            explanation=candidate.explanation,
            evidence=candidate.evidence_json,
            detector_name=candidate.detector_name,
            detector_version=candidate.detector_version,
            model_version=candidate.model_version,
        )


class AccountingRecommendationResponse(BaseModel):
    id: UUID
    recommendation_type: str
    recommended_value: str
    confidence: str | None
    explanation: str
    evidence: dict[str, Any]
    rule_name: str
    rule_version: str
    model_version: str | None

    @classmethod
    def from_recommendation(
        cls,
        recommendation: AccountingRecommendation,
    ) -> AccountingRecommendationResponse:
        return cls(
            id=recommendation.id,
            recommendation_type=recommendation.recommendation_type,
            recommended_value=recommendation.recommended_value,
            confidence=_decimal_to_string(recommendation.confidence),
            explanation=recommendation.explanation,
            evidence=recommendation.evidence_json,
            rule_name=recommendation.rule_name,
            rule_version=recommendation.rule_version,
            model_version=recommendation.model_version,
        )


class ProposedJournalLineResponse(BaseModel):
    id: UUID
    line_number: int
    account_reference: str
    debit_amount: str
    credit_amount: str
    tax_code_reference: str | None
    cost_centre_reference: str | None
    explanation: str
    lineage: dict[str, Any]

    @classmethod
    def from_line(cls, line: ProposedJournalLine) -> ProposedJournalLineResponse:
        return cls(
            id=line.id,
            line_number=line.line_number,
            account_reference=line.account_reference,
            debit_amount=_required_decimal_to_string(line.debit_amount),
            credit_amount=_required_decimal_to_string(line.credit_amount),
            tax_code_reference=line.tax_code_reference,
            cost_centre_reference=line.cost_centre_reference,
            explanation=line.explanation,
            lineage=line.lineage_json,
        )


class ProposedJournalResponse(BaseModel):
    id: UUID
    currency: str
    total_debits: str
    total_credits: str
    balance_status: str
    is_balanced: bool
    explanation: str
    lines: list[ProposedJournalLineResponse]

    @classmethod
    def from_journal(
        cls,
        journal: ProposedJournal,
        lines: list[ProposedJournalLine],
    ) -> ProposedJournalResponse:
        return cls(
            id=journal.id,
            currency=journal.currency,
            total_debits=_required_decimal_to_string(journal.total_debits),
            total_credits=_required_decimal_to_string(journal.total_credits),
            balance_status=journal.balance_status,
            is_balanced=journal.is_balanced,
            explanation=journal.explanation,
            lines=[ProposedJournalLineResponse.from_line(line) for line in lines],
        )


class AccountingDecisionRunSummaryResponse(BaseModel):
    id: UUID
    client_id: UUID
    document_id: UUID
    extraction_run_id: UUID
    status: str
    engine_name: str
    engine_version: str
    model_version: str | None
    source_sha256: str
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None
    request_id: str | None
    created_at: datetime

    @classmethod
    def from_run(cls, run: AccountingDecisionRun) -> AccountingDecisionRunSummaryResponse:
        return cls(
            id=run.id,
            client_id=run.client_id,
            document_id=run.document_id,
            extraction_run_id=run.extraction_run_id,
            status=run.status,
            engine_name=run.engine_name,
            engine_version=run.engine_version,
            model_version=run.model_version,
            source_sha256=run.source_sha256,
            started_at=run.started_at,
            completed_at=run.completed_at,
            failure_code=run.failure_code,
            request_id=run.request_id,
            created_at=run.created_at,
        )


class AccountingDecisionRunResponse(AccountingDecisionRunSummaryResponse):
    findings: list[AccountingDecisionFindingResponse]
    supplier_match: SupplierMatchResponse
    duplicate_candidates: list[DuplicateCandidateResponse]
    recommendations: list[AccountingRecommendationResponse]
    proposed_journal: ProposedJournalResponse | None

    @classmethod
    def from_bundle(cls, bundle: AccountingDecisionRunBundle) -> AccountingDecisionRunResponse:
        summary = AccountingDecisionRunSummaryResponse.from_run(bundle.run)
        return cls(
            **summary.model_dump(),
            findings=[
                AccountingDecisionFindingResponse.from_finding(finding)
                for finding in bundle.findings
            ],
            supplier_match=SupplierMatchResponse.from_candidates(bundle.supplier_match_candidates),
            duplicate_candidates=[
                DuplicateCandidateResponse.from_candidate(candidate)
                for candidate in bundle.duplicate_candidates
            ],
            recommendations=[
                AccountingRecommendationResponse.from_recommendation(recommendation)
                for recommendation in bundle.recommendations
            ],
            proposed_journal=(
                ProposedJournalResponse.from_journal(
                    bundle.proposed_journal,
                    bundle.proposed_journal_lines,
                )
                if bundle.proposed_journal is not None
                else None
            ),
        )


def _decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _required_decimal_to_string(value: Decimal) -> str:
    return format(value, "f")
