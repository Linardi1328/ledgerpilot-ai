from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.accounting.engine import AccountingDecisionEngine
from ledgerpilot.accounting.rules import AccountingDecisionPolicy
from ledgerpilot.accounting.states import (
    AccountingDecisionRunStatus,
    transition_accounting_decision_status,
)
from ledgerpilot.accounting.types import (
    AccountingDecisionFailureCode,
    AccountingDecisionOutput,
    EffectiveExtractionValue,
    PriorDecisionSnapshot,
)
from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.service import AuditService
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.extraction.states import is_extraction_ready_for_downstream
from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.accounting import (
    AccountingDecisionFinding,
    AccountingDecisionRun,
    AccountingDuplicateCandidate,
    AccountingRecommendation,
    AccountingSupplierMatchCandidate,
    ProposedJournal,
    ProposedJournalLine,
)
from ledgerpilot.persistence.models.extraction import (
    ExtractedField,
    ExtractionFieldCorrection,
    ExtractionRun,
)
from ledgerpilot.persistence.repositories.accounting import AccountingRepository
from ledgerpilot.persistence.repositories.clients import ClientRepository
from ledgerpilot.persistence.repositories.extraction import ExtractionRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccountingDecisionRunBundle:
    run: AccountingDecisionRun
    findings: list[AccountingDecisionFinding]
    supplier_match_candidates: list[AccountingSupplierMatchCandidate]
    duplicate_candidates: list[AccountingDuplicateCandidate]
    recommendations: list[AccountingRecommendation]
    proposed_journal: ProposedJournal | None
    proposed_journal_lines: list[ProposedJournalLine]


class AccountingDecisionService:
    def __init__(
        self,
        *,
        session: Session,
        policy: AccountingDecisionPolicy,
    ) -> None:
        self._session = session
        self._policy = policy
        self._clients = ClientRepository(session)
        self._extractions = ExtractionRepository(session)
        self._accounting = AccountingRepository(session)
        self._audit = AuditService(session)

    def start_decision_run(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        request_id: str | None,
    ) -> AccountingDecisionRunBundle:
        self._require_client_access(principal=principal, client_id=client_id)
        extraction_run = self._get_extraction_run_or_404(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
        )
        if not is_extraction_ready_for_downstream(extraction_run.status):
            raise ApiError(
                status_code=409,
                code=AccountingDecisionFailureCode.SOURCE_NOT_ELIGIBLE.value,
                message="Extraction run is not eligible for accounting decisions.",
            )

        run = self._new_run(
            principal=principal,
            extraction_run=extraction_run,
            request_id=request_id,
        )
        self._accounting.add_run(run)
        self._transition(run, AccountingDecisionRunStatus.RUNNING)
        self._record_decision_event(
            event_type=AuditEventType.ACCOUNTING_DECISION_STARTED,
            principal=principal,
            client_id=client_id,
            run=run,
            request_id=request_id,
            metadata=_run_event_metadata(run),
        )
        try:
            self._session.flush()
        except SQLAlchemyError as exc:
            self._raise_persistence_error(run=run, request_id=request_id, exc=exc)

        try:
            output = self._run_engine(extraction_run=extraction_run)
        except Exception as exc:
            self._fail_run(
                run=run,
                principal=principal,
                client_id=client_id,
                request_id=request_id,
                failure_code=AccountingDecisionFailureCode.DECISION_ENGINE_FAILED,
            )
            logger.info(
                "Accounting decision engine failed",
                extra={
                    "request_id": request_id,
                    "decision_run_id": str(run.id),
                    "failure_code": AccountingDecisionFailureCode.DECISION_ENGINE_FAILED.value,
                    "exception_type": type(exc).__name__,
                },
            )
            self._commit_or_raise_persistence(run=run, request_id=request_id)
            raise ApiError(
                status_code=503,
                code=AccountingDecisionFailureCode.DECISION_ENGINE_FAILED.value,
                message="Accounting decision engine failed.",
            ) from exc

        self._persist_output(run=run, output=output)
        self._transition(run, AccountingDecisionRunStatus.SUCCEEDED)
        self._record_decision_event(
            event_type=AuditEventType.ACCOUNTING_DECISION_SUCCEEDED,
            principal=principal,
            client_id=client_id,
            run=run,
            request_id=request_id,
            metadata={
                **_run_event_metadata(run),
                "finding_count": len(output.findings),
                "supplier_candidate_count": len(output.supplier_match.candidates),
                "duplicate_candidate_count": len(output.duplicate_candidates),
                "recommendation_count": len(output.recommendations),
                "journal_balance_status": (
                    output.proposed_journal.balance_status.value
                    if output.proposed_journal is not None
                    else None
                ),
                "journal_balanced": (
                    output.proposed_journal.is_balanced
                    if output.proposed_journal is not None
                    else None
                ),
            },
        )
        self._commit_or_raise_persistence(run=run, request_id=request_id)
        return self.get_decision_run(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=run.id,
        )

    def list_decision_runs(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
    ) -> list[AccountingDecisionRun]:
        self._require_client_access(principal=principal, client_id=client_id)
        self._get_extraction_run_or_404(
            principal=principal,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
        )
        return self._accounting.list_runs_for_extraction(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
        )

    def get_decision_run(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
        decision_run_id: UUID,
    ) -> AccountingDecisionRunBundle:
        self._require_client_access(principal=principal, client_id=client_id)
        run = self._accounting.get_run_for_extraction(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
        )
        if run is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return AccountingDecisionRunBundle(
            run=run,
            findings=self._accounting.list_findings_for_run(
                firm_id=principal.firm_id,
                client_id=client_id,
                document_id=document_id,
                extraction_run_id=extraction_run_id,
                decision_run_id=decision_run_id,
            ),
            supplier_match_candidates=self._accounting.list_supplier_match_candidates_for_run(
                firm_id=principal.firm_id,
                client_id=client_id,
                document_id=document_id,
                extraction_run_id=extraction_run_id,
                decision_run_id=decision_run_id,
            ),
            duplicate_candidates=self._accounting.list_duplicate_candidates_for_run(
                firm_id=principal.firm_id,
                client_id=client_id,
                document_id=document_id,
                extraction_run_id=extraction_run_id,
                decision_run_id=decision_run_id,
            ),
            recommendations=self._accounting.list_recommendations_for_run(
                firm_id=principal.firm_id,
                client_id=client_id,
                document_id=document_id,
                extraction_run_id=extraction_run_id,
                decision_run_id=decision_run_id,
            ),
            proposed_journal=self._accounting.get_proposed_journal_for_run(
                firm_id=principal.firm_id,
                client_id=client_id,
                document_id=document_id,
                extraction_run_id=extraction_run_id,
                decision_run_id=decision_run_id,
            ),
            proposed_journal_lines=self._accounting.list_proposed_journal_lines_for_run(
                firm_id=principal.firm_id,
                client_id=client_id,
                document_id=document_id,
                extraction_run_id=extraction_run_id,
                decision_run_id=decision_run_id,
            ),
        )

    def _run_engine(self, *, extraction_run: ExtractionRun) -> AccountingDecisionOutput:
        fields = self._extractions.list_fields_for_run(
            firm_id=extraction_run.firm_id,
            client_id=extraction_run.client_id,
            document_id=extraction_run.document_id,
            run_id=extraction_run.id,
        )
        corrections = self._extractions.list_corrections_for_run(
            firm_id=extraction_run.firm_id,
            client_id=extraction_run.client_id,
            document_id=extraction_run.document_id,
            run_id=extraction_run.id,
        )
        effective_values = build_effective_extraction_values(fields, corrections)
        prior_snapshots = self._prior_decision_snapshots(extraction_run)
        return AccountingDecisionEngine(self._policy).decide(
            firm_id=extraction_run.firm_id,
            client_id=extraction_run.client_id,
            document_id=extraction_run.document_id,
            extraction_run_id=extraction_run.id,
            source_sha256=extraction_run.source_sha256,
            effective_values=effective_values,
            prior_snapshots=prior_snapshots,
        )

    def _prior_decision_snapshots(
        self,
        extraction_run: ExtractionRun,
    ) -> tuple[PriorDecisionSnapshot, ...]:
        snapshots: list[PriorDecisionSnapshot] = []
        prior_runs = self._accounting.list_succeeded_runs_for_client(
            firm_id=extraction_run.firm_id,
            client_id=extraction_run.client_id,
        )
        for prior_run in prior_runs:
            fields = self._extractions.list_fields_for_run(
                firm_id=prior_run.firm_id,
                client_id=prior_run.client_id,
                document_id=prior_run.document_id,
                run_id=prior_run.extraction_run_id,
            )
            corrections = self._extractions.list_corrections_for_run(
                firm_id=prior_run.firm_id,
                client_id=prior_run.client_id,
                document_id=prior_run.document_id,
                run_id=prior_run.extraction_run_id,
            )
            snapshots.append(
                PriorDecisionSnapshot(
                    decision_run_id=prior_run.id,
                    document_id=prior_run.document_id,
                    extraction_run_id=prior_run.extraction_run_id,
                    source_sha256=prior_run.source_sha256,
                    effective_values=build_effective_extraction_values(fields, corrections),
                )
            )
        return tuple(snapshots)

    def _persist_output(
        self,
        *,
        run: AccountingDecisionRun,
        output: AccountingDecisionOutput,
    ) -> None:
        for finding in output.findings:
            self._accounting.add_finding(
                AccountingDecisionFinding(
                    decision_run_id=run.id,
                    firm_id=run.firm_id,
                    client_id=run.client_id,
                    document_id=run.document_id,
                    extraction_run_id=run.extraction_run_id,
                    code=finding.code.value,
                    severity=finding.severity.value,
                    field_path=finding.field_path,
                    description=finding.description,
                    evidence_json=finding.evidence or {},
                )
            )
        for supplier_candidate in output.supplier_match.candidates:
            self._accounting.add_supplier_match_candidate(
                AccountingSupplierMatchCandidate(
                    decision_run_id=run.id,
                    firm_id=run.firm_id,
                    client_id=run.client_id,
                    document_id=run.document_id,
                    extraction_run_id=run.extraction_run_id,
                    supplier_reference=supplier_candidate.supplier_reference,
                    supplier_name=supplier_candidate.supplier_name,
                    confidence=supplier_candidate.confidence,
                    explanation=supplier_candidate.explanation,
                    evidence_json=supplier_candidate.evidence,
                    matcher_name=supplier_candidate.matcher_name,
                    matcher_version=supplier_candidate.matcher_version,
                    model_version=supplier_candidate.model_version,
                    is_confident=supplier_candidate.is_confident,
                )
            )
        for duplicate_candidate in output.duplicate_candidates:
            self._accounting.add_duplicate_candidate(
                AccountingDuplicateCandidate(
                    decision_run_id=run.id,
                    firm_id=run.firm_id,
                    client_id=run.client_id,
                    document_id=run.document_id,
                    extraction_run_id=run.extraction_run_id,
                    candidate_document_id=duplicate_candidate.candidate_document_id,
                    candidate_extraction_run_id=duplicate_candidate.candidate_extraction_run_id,
                    candidate_decision_run_id=duplicate_candidate.candidate_decision_run_id,
                    confidence=duplicate_candidate.confidence,
                    explanation=duplicate_candidate.explanation,
                    evidence_json=duplicate_candidate.evidence,
                    detector_name=duplicate_candidate.detector_name,
                    detector_version=duplicate_candidate.detector_version,
                    model_version=duplicate_candidate.model_version,
                )
            )
        for recommendation in output.recommendations:
            self._accounting.add_recommendation(
                AccountingRecommendation(
                    decision_run_id=run.id,
                    firm_id=run.firm_id,
                    client_id=run.client_id,
                    document_id=run.document_id,
                    extraction_run_id=run.extraction_run_id,
                    recommendation_type=recommendation.recommendation_type.value,
                    recommended_value=recommendation.recommended_value,
                    confidence=recommendation.confidence,
                    explanation=recommendation.explanation,
                    evidence_json=recommendation.evidence,
                    rule_name=recommendation.rule_name,
                    rule_version=recommendation.rule_version,
                    model_version=recommendation.model_version,
                )
            )
        if output.proposed_journal is None:
            return
        journal = ProposedJournal(
            id=uuid.uuid4(),
            decision_run_id=run.id,
            firm_id=run.firm_id,
            client_id=run.client_id,
            document_id=run.document_id,
            extraction_run_id=run.extraction_run_id,
            currency=output.proposed_journal.currency,
            total_debits=output.proposed_journal.total_debits,
            total_credits=output.proposed_journal.total_credits,
            balance_status=output.proposed_journal.balance_status.value,
            is_balanced=output.proposed_journal.is_balanced,
            explanation=output.proposed_journal.explanation,
        )
        self._accounting.add_proposed_journal(journal)
        for line in output.proposed_journal.lines:
            self._accounting.add_proposed_journal_line(
                ProposedJournalLine(
                    proposed_journal_id=journal.id,
                    decision_run_id=run.id,
                    firm_id=run.firm_id,
                    client_id=run.client_id,
                    document_id=run.document_id,
                    extraction_run_id=run.extraction_run_id,
                    line_number=line.line_number,
                    account_reference=line.account_reference,
                    debit_amount=line.debit_amount,
                    credit_amount=line.credit_amount,
                    tax_code_reference=line.tax_code_reference,
                    cost_centre_reference=line.cost_centre_reference,
                    explanation=line.explanation,
                    lineage_json=line.lineage,
                )
            )

    def _get_extraction_run_or_404(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        extraction_run_id: UUID,
    ) -> ExtractionRun:
        extraction_run = self._extractions.get_run_for_document(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            run_id=extraction_run_id,
        )
        if extraction_run is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return extraction_run

    def _require_client_access(self, *, principal: Principal, client_id: UUID) -> None:
        client = self._clients.get_authorized_client(
            membership_id=principal.membership_id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    def _new_run(
        self,
        *,
        principal: Principal,
        extraction_run: ExtractionRun,
        request_id: str | None,
    ) -> AccountingDecisionRun:
        return AccountingDecisionRun(
            id=uuid.uuid4(),
            firm_id=extraction_run.firm_id,
            client_id=extraction_run.client_id,
            document_id=extraction_run.document_id,
            extraction_run_id=extraction_run.id,
            initiated_by_user_id=principal.user_id,
            initiated_by_membership_id=principal.membership_id,
            status=AccountingDecisionRunStatus.PENDING.value,
            engine_name=self._policy.engine_name,
            engine_version=self._policy.engine_version,
            model_version=None,
            source_sha256=extraction_run.source_sha256,
            request_id=request_id,
        )

    def _transition(
        self,
        run: AccountingDecisionRun,
        status: AccountingDecisionRunStatus,
    ) -> None:
        current_status = AccountingDecisionRunStatus(run.status)
        run.status = transition_accounting_decision_status(current_status, status).value
        if status == AccountingDecisionRunStatus.RUNNING:
            run.started_at = datetime.now(UTC)
        if status in {AccountingDecisionRunStatus.SUCCEEDED, AccountingDecisionRunStatus.FAILED}:
            run.completed_at = datetime.now(UTC)

    def _fail_run(
        self,
        *,
        run: AccountingDecisionRun,
        principal: Principal,
        client_id: UUID,
        request_id: str | None,
        failure_code: AccountingDecisionFailureCode,
    ) -> None:
        self._transition(run, AccountingDecisionRunStatus.FAILED)
        run.failure_code = failure_code.value
        self._record_decision_event(
            event_type=AuditEventType.ACCOUNTING_DECISION_FAILED,
            principal=principal,
            client_id=client_id,
            run=run,
            request_id=request_id,
            metadata={**_run_event_metadata(run), "failure_code": failure_code.value},
        )

    def _commit_or_raise_persistence(
        self,
        *,
        run: AccountingDecisionRun,
        request_id: str | None,
    ) -> None:
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._raise_persistence_error(run=run, request_id=request_id, exc=exc)

    def _raise_persistence_error(
        self,
        *,
        run: AccountingDecisionRun,
        request_id: str | None,
        exc: SQLAlchemyError,
    ) -> None:
        self._session.rollback()
        logger.warning(
            "Accounting decision persistence failed",
            extra={
                "request_id": request_id,
                "decision_run_id": str(run.id),
                "failure_code": AccountingDecisionFailureCode.PERSISTENCE_FAILED.value,
                "exception_type": type(exc).__name__,
            },
        )
        raise ApiError(
            status_code=503,
            code=AccountingDecisionFailureCode.PERSISTENCE_FAILED.value,
            message="Accounting decision state could not be persisted.",
        ) from exc

    def _record_decision_event(
        self,
        *,
        event_type: AuditEventType,
        principal: Principal,
        client_id: UUID,
        run: AccountingDecisionRun,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit.record_event(
            firm_id=principal.firm_id,
            client_id=client_id,
            actor_user_id=principal.user_id,
            event_type=event_type.value,
            target_type="accounting_decision_run",
            target_id=str(run.id),
            request_id=request_id,
            metadata=metadata,
        )


def build_effective_extraction_values(
    fields: list[ExtractedField],
    corrections: list[ExtractionFieldCorrection],
) -> dict[str, EffectiveExtractionValue]:
    latest_correction_by_field_id: dict[UUID, ExtractionFieldCorrection] = {}
    for correction in corrections:
        latest = latest_correction_by_field_id.get(correction.field_id)
        if latest is None or correction.revision_number > latest.revision_number:
            latest_correction_by_field_id[correction.field_id] = correction

    effective_values: dict[str, EffectiveExtractionValue] = {}
    for field in fields:
        latest = latest_correction_by_field_id.get(field.id)
        effective_values[field.field_path] = EffectiveExtractionValue(
            field_id=field.id,
            field_path=field.field_path,
            value_type=latest.corrected_value_type if latest is not None else field.value_type,
            raw_value=latest.corrected_raw_value if latest is not None else field.raw_value,
            normalized_value=(
                latest.corrected_normalized_value if latest is not None else field.normalized_value
            ),
            confidence=field.confidence,
            source_page_number=field.source_page_number,
            corrected=latest is not None,
            latest_correction_id=latest.id if latest is not None else None,
            latest_revision_number=latest.revision_number if latest is not None else None,
        )
    return effective_values


def _run_event_metadata(run: AccountingDecisionRun) -> dict[str, object]:
    return {
        "decision_run_id": str(run.id),
        "document_id": str(run.document_id),
        "extraction_run_id": str(run.extraction_run_id),
        "engine_name": run.engine_name,
        "engine_version": run.engine_version,
    }
