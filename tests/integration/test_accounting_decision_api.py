from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import BinaryIO
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ledgerpilot.accounting.rules import SyntheticAccountingDecisionPolicy
from ledgerpilot.api.app import create_app
from ledgerpilot.api.middleware import REQUEST_ID_HEADER
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.core.config import Settings
from ledgerpilot.extraction.protocol import ExtractionProvider, ExtractionRequestContext
from ledgerpilot.extraction.states import ExtractionRunStatus
from ledgerpilot.extraction.types import (
    ExtractionProviderMetadata,
    ExtractionProviderResult,
    ExtractionValueType,
    ProviderExtractedField,
)
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.accounting import AccountingDecisionRun
from ledgerpilot.persistence.models.documents import DocumentFile
from ledgerpilot.persistence.models.extraction import ExtractedField, ExtractionRun
from ledgerpilot.persistence.repositories.audit import AuditRepository
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from ledgerpilot.storage.local import LocalDocumentStorage
from tests.conftest import IdentitySeed

PDF_BYTES = b"%PDF-1.4\n% synthetic pdf for LedgerPilot Phase 4 accounting tests\n"


class StaticExtractionProvider:
    def __init__(
        self,
        *,
        fields: tuple[ProviderExtractedField, ...],
        provider_name: str = "synthetic_static_accounting_provider",
    ) -> None:
        self._fields = fields
        self._metadata = ExtractionProviderMetadata(
            provider_name=provider_name,
            provider_version="0.1.0",
            model_version=None,
            extraction_schema_version="ledgerpilot.extraction.v1",
        )

    @property
    def metadata(self) -> ExtractionProviderMetadata:
        return self._metadata

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        del context
        source_file.read(1)
        return ExtractionProviderResult(metadata=self._metadata, fields=self._fields)


def test_accountant_runs_accounting_decision_for_downstream_ready_extraction(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    extraction_payload = _start_extraction(client, identity_seed, document_id=document_id).json()

    response = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=UUID(extraction_payload["id"]),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["engine_name"] == "synthetic_accounting_decision_engine"
    assert payload["source_sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()
    assert payload["supplier_match"]["status"] == "confident_match"
    assert payload["proposed_journal"]["is_balanced"] is True
    assert {line["account_reference"] for line in payload["proposed_journal"]["lines"]} == {
        "expense:office_supplies",
        "liability:accounts_payable",
    }
    assert {finding["code"] for finding in payload["findings"]} == {"tax_review_required"}

    run = db_session.get(AccountingDecisionRun, UUID(payload["id"]))
    assert run is not None
    assert run.extraction_run_id == UUID(extraction_payload["id"])
    assert run.started_at is not None
    assert run.completed_at is not None
    assert run.initiated_by_user_id == identity_seed.accountant.id
    assert run.initiated_by_membership_id == identity_seed.accountant_membership.id

    events = [
        event
        for event in AuditRepository(db_session).list_for_firm(firm_id=identity_seed.firm_a.id)
        if event.target_id == payload["id"]
    ]
    assert {event.event_type for event in events} == {
        AuditEventType.ACCOUNTING_DECISION_STARTED.value,
        AuditEventType.ACCOUNTING_DECISION_SUCCEEDED.value,
    }
    for event in events:
        assert "RM 100.00" not in str(event.metadata_json)
        assert "SYN-INV-001" not in str(event.metadata_json)
        assert "Synthetic Office Supplies" not in str(event.metadata_json)


def test_failed_and_non_ready_extraction_runs_are_rejected(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    document_file = db_session.scalars(
        select(DocumentFile).where(DocumentFile.document_id == document_id)
    ).one()
    failed_run = _direct_extraction_run(
        db_session,
        identity_seed,
        document_file=document_file,
        status=ExtractionRunStatus.FAILED,
    )
    pending_run = _direct_extraction_run(
        db_session,
        identity_seed,
        document_file=document_file,
        status=ExtractionRunStatus.PENDING,
    )

    failed_response = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=failed_run.id,
    )
    pending_response = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=pending_run.id,
    )

    assert failed_response.status_code == 409
    assert failed_response.json()["error"]["code"] == "source_not_eligible"
    assert pending_response.status_code == 409
    assert pending_response.json()["error"]["code"] == "source_not_eligible"
    assert db_session.scalars(select(AccountingDecisionRun)).all() == []


def test_effective_corrected_value_is_used_without_mutating_original_extraction(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    extraction_payload = _start_extraction(client, identity_seed, document_id=document_id).json()
    total_field = next(
        field for field in extraction_payload["fields"] if field["field_path"] == "invoice.total"
    )

    correction = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/"
        f"{extraction_payload['id']}/fields/{total_field['id']}/corrections",
        headers=_auth_headers(identity_seed, request_id="req-phase4-correction"),
        json={
            "corrected_raw_value": "RM 101.00",
            "corrected_normalized_value": "101.00",
            "corrected_value_type": "decimal",
            "reason": "Synthetic correction before accounting decision.",
        },
    )
    assert correction.status_code == 201

    response = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=UUID(extraction_payload["id"]),
    )

    assert response.status_code == 201
    journal = response.json()["proposed_journal"]
    assert Decimal(journal["total_debits"]) == Decimal("101.0000")
    assert Decimal(journal["total_credits"]) == Decimal("101.0000")
    stored_field = db_session.get(ExtractedField, UUID(total_field["id"]))
    assert stored_field is not None
    assert stored_field.raw_value == "RM 100.00"
    assert stored_field.normalized_value == "100.00"


def test_rerunning_accounting_decisions_creates_new_immutable_runs(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    extraction_payload = _start_extraction(client, identity_seed, document_id=document_id).json()
    extraction_run_id = UUID(extraction_payload["id"])

    first = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
    )
    second = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
    )
    list_response = client.get(
        _decision_url(identity_seed.client_a.id, document_id, extraction_run_id),
        headers=_auth_headers(identity_seed),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    first_run = db_session.get(AccountingDecisionRun, UUID(first.json()["id"]))
    assert first_run is not None
    assert first_run.status == "succeeded"
    assert list_response.status_code == 200
    assert {run["id"] for run in list_response.json()} == {
        first.json()["id"],
        second.json()["id"],
    }


def test_required_field_arithmetic_and_unknown_supplier_findings_are_structured(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    provider = StaticExtractionProvider(
        fields=_invoice_fields(
            include_invoice_number=False,
            supplier_name="Synthetic Unknown Supplier Sdn. Bhd.",
            subtotal="90.00",
            tax="10.01",
            total="100.00",
        )
    )
    with _create_client_with_provider(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        provider=provider,
    ) as test_client:
        document_id = _upload_document(test_client, identity_seed)
        extraction_payload = _start_extraction(
            test_client,
            identity_seed,
            document_id=document_id,
        ).json()
        response = _start_decision(
            test_client,
            identity_seed,
            document_id=document_id,
            extraction_run_id=UUID(extraction_payload["id"]),
        )

    assert response.status_code == 201
    findings = {finding["code"]: finding for finding in response.json()["findings"]}
    assert findings["missing_required_field"]["field_path"] == "invoice.number"
    assert findings["arithmetic_mismatch"]["evidence"]["calculated_total"] == "100.01"
    assert findings["new_supplier"]["field_path"] == "supplier.name"
    assert findings["unknown_account_mapping"]["field_path"] == "supplier.name"
    assert response.json()["supplier_match"]["status"] == "no_match"
    assert response.json()["proposed_journal"] is None


def test_duplicate_candidate_detected_without_auto_rejecting_document(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    first_document_id = _upload_document(client, identity_seed, filename="synthetic-a.pdf")
    first_extraction_payload = _start_extraction(
        client,
        identity_seed,
        document_id=first_document_id,
    ).json()
    first_decision = _start_decision(
        client,
        identity_seed,
        document_id=first_document_id,
        extraction_run_id=UUID(first_extraction_payload["id"]),
    )
    second_document_id = _upload_document(client, identity_seed, filename="synthetic-b.pdf")
    second_extraction_payload = _start_extraction(
        client,
        identity_seed,
        document_id=second_document_id,
    ).json()

    second_decision = _start_decision(
        client,
        identity_seed,
        document_id=second_document_id,
        extraction_run_id=UUID(second_extraction_payload["id"]),
    )

    assert first_decision.status_code == 201
    assert second_decision.status_code == 201
    payload = second_decision.json()
    assert payload["status"] == "succeeded"
    assert len(payload["duplicate_candidates"]) == 1
    assert payload["duplicate_candidates"][0]["candidate_document_id"] == str(first_document_id)
    assert "source_sha256" in payload["duplicate_candidates"][0]["evidence"]["matched_signals"]
    assert "possible_duplicate" in {finding["code"] for finding in payload["findings"]}


def test_nonduplicate_invoice_is_not_reported_as_duplicate(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    first_provider = StaticExtractionProvider(
        fields=_invoice_fields(invoice_number="SYN-FIRST-001", total="100.00"),
        provider_name="synthetic_first_invoice_provider",
    )
    second_provider = StaticExtractionProvider(
        fields=_invoice_fields(
            supplier_name="Synthetic Different Supplier Sdn. Bhd.",
            invoice_number="SYN-SECOND-001",
            total="101.00",
        ),
        provider_name="synthetic_second_invoice_provider",
    )
    with _create_client_with_provider(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        provider=first_provider,
    ) as first_client:
        first_document_id = _upload_document(first_client, identity_seed, content=PDF_BYTES + b"1")
        first_extraction_payload = _start_extraction(
            first_client,
            identity_seed,
            document_id=first_document_id,
        ).json()
        first_decision = _start_decision(
            first_client,
            identity_seed,
            document_id=first_document_id,
            extraction_run_id=UUID(first_extraction_payload["id"]),
        )
    with _create_client_with_provider(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        provider=second_provider,
    ) as second_client:
        second_document_id = _upload_document(
            second_client,
            identity_seed,
            content=PDF_BYTES + b"2",
        )
        second_extraction_payload = _start_extraction(
            second_client,
            identity_seed,
            document_id=second_document_id,
        ).json()
        second_decision = _start_decision(
            second_client,
            identity_seed,
            document_id=second_document_id,
            extraction_run_id=UUID(second_extraction_payload["id"]),
        )

    assert first_decision.status_code == 201
    assert second_decision.status_code == 201
    assert second_decision.json()["duplicate_candidates"] == []
    assert "possible_duplicate" not in {
        finding["code"] for finding in second_decision.json()["findings"]
    }


def test_unbalanced_journal_is_persisted_as_flagged_not_valid(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    policy = SyntheticAccountingDecisionPolicy(
        synthetic_journal_credit_adjustment=Decimal("0.01"),
    )
    with TestClient(
        create_app(
            settings=settings,
            session_factory=session_factory,
            document_storage=document_storage,
            accounting_decision_policy=policy,
        )
    ) as test_client:
        document_id = _upload_document(test_client, identity_seed)
        extraction_payload = _start_extraction(
            test_client,
            identity_seed,
            document_id=document_id,
        ).json()
        response = _start_decision(
            test_client,
            identity_seed,
            document_id=document_id,
            extraction_run_id=UUID(extraction_payload["id"]),
        )

    assert response.status_code == 201
    journal = response.json()["proposed_journal"]
    assert journal["is_balanced"] is False
    assert journal["balance_status"] == "unbalanced"
    assert Decimal(journal["total_credits"]) == Decimal("100.0100")
    assert "unbalanced_journal" in {finding["code"] for finding in response.json()["findings"]}


def test_accounting_decision_execution_rbac(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    senior_subject = _add_senior_reviewer(db_session, identity_seed)
    document_id = _upload_document(client, identity_seed)
    extraction_payload = _start_extraction(client, identity_seed, document_id=document_id).json()
    extraction_run_id = UUID(extraction_payload["id"])

    senior_response = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        subject=senior_subject,
    )
    assert senior_response.status_code == 201

    for subject in (
        identity_seed.admin.external_subject,
        identity_seed.auditor.external_subject,
        identity_seed.submitter.external_subject,
    ):
        response = _start_decision(
            client,
            identity_seed,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            subject=subject,
        )
        assert response.status_code == 403


def test_cross_client_accounting_decision_access_is_denied(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    extraction_payload = _start_extraction(client, identity_seed, document_id=document_id).json()

    response = _start_decision(
        client,
        identity_seed,
        client_id=identity_seed.client_b.id,
        document_id=document_id,
        extraction_run_id=UUID(extraction_payload["id"]),
    )

    assert response.status_code == 403


def _auth_headers(
    identity_seed: IdentitySeed,
    *,
    subject: str | None = None,
    firm_id: UUID | None = None,
    request_id: str = "req-accounting-test",
) -> dict[str, str]:
    return {
        "X-LedgerPilot-Dev-Subject": subject or identity_seed.accountant.external_subject,
        "X-LedgerPilot-Firm": str(firm_id or identity_seed.firm_a.id),
        REQUEST_ID_HEADER: request_id,
    }


def _upload_document(
    client: TestClient,
    identity_seed: IdentitySeed,
    *,
    filename: str = "synthetic-accounting-source.pdf",
    content: bytes = PDF_BYTES,
) -> UUID:
    response = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents",
        headers=_auth_headers(identity_seed),
        files={"file": (filename, content, "application/pdf")},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _start_extraction(
    client: TestClient,
    identity_seed: IdentitySeed,
    *,
    document_id: UUID,
):
    return client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions",
        headers=_auth_headers(identity_seed, request_id="req-accounting-extraction"),
    )


def _start_decision(
    client: TestClient,
    identity_seed: IdentitySeed,
    *,
    document_id: UUID,
    extraction_run_id: UUID,
    client_id: UUID | None = None,
    subject: str | None = None,
):
    target_client_id = client_id or identity_seed.client_a.id
    return client.post(
        _decision_url(target_client_id, document_id, extraction_run_id),
        headers=_auth_headers(
            identity_seed,
            subject=subject,
            request_id="req-accounting-decision",
        ),
    )


def _decision_url(client_id: UUID, document_id: UUID, extraction_run_id: UUID) -> str:
    return (
        f"/api/v1/clients/{client_id}/documents/{document_id}/extractions/"
        f"{extraction_run_id}/accounting-decisions"
    )


def _create_client_with_provider(
    *,
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    provider: ExtractionProvider,
) -> TestClient:
    app = create_app(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        extraction_provider=provider,
    )
    return TestClient(app)


def _add_senior_reviewer(db_session: Session, identity_seed: IdentitySeed) -> str:
    repository = IdentityRepository(db_session)
    senior = repository.add_user(external_subject="dev-senior-accounting")
    db_session.flush()
    membership = repository.add_membership(
        user_id=senior.id,
        firm_id=identity_seed.firm_a.id,
        role=Role.SENIOR_REVIEWER.value,
    )
    db_session.flush()
    repository.grant_client_access(
        membership_id=membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
    )
    db_session.commit()
    return senior.external_subject


def _direct_extraction_run(
    db_session: Session,
    identity_seed: IdentitySeed,
    *,
    document_file: DocumentFile,
    status: ExtractionRunStatus,
) -> ExtractionRun:
    now = datetime.now(UTC)
    run = ExtractionRun(
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
        document_id=document_file.document_id,
        document_file_id=document_file.id,
        initiated_by_user_id=identity_seed.accountant.id,
        initiated_by_membership_id=identity_seed.accountant_membership.id,
        status=status.value,
        provider_name="synthetic_direct_provider",
        provider_version="0.1.0",
        model_version=None,
        extraction_schema_version="ledgerpilot.extraction.v1",
        source_sha256=document_file.sha256,
        started_at=now if status != ExtractionRunStatus.PENDING else None,
        completed_at=(
            now if status in {ExtractionRunStatus.SUCCEEDED, ExtractionRunStatus.FAILED} else None
        ),
        failure_code="provider_failed" if status == ExtractionRunStatus.FAILED else None,
    )
    db_session.add(run)
    db_session.commit()
    return run


def _invoice_fields(
    *,
    include_invoice_number: bool = True,
    supplier_name: str = "Synthetic Office Supplies Sdn. Bhd.",
    invoice_number: str = "SYN-INV-001",
    subtotal: str | None = None,
    tax: str | None = None,
    total: str = "100.00",
) -> tuple[ProviderExtractedField, ...]:
    fields = [
        ProviderExtractedField(
            field_path="document.type",
            value_type=ExtractionValueType.TEXT.value,
            raw_value="synthetic_purchase_invoice",
            normalized_value="purchase_invoice",
            confidence=Decimal("0.9000"),
            source_page_number=1,
        ),
        ProviderExtractedField(
            field_path="supplier.name",
            value_type=ExtractionValueType.TEXT.value,
            raw_value=supplier_name,
            confidence=Decimal("0.9000"),
            source_page_number=1,
        ),
        ProviderExtractedField(
            field_path="invoice.date",
            value_type=ExtractionValueType.DATE.value,
            raw_value="2026-08-11",
            normalized_value="2026-08-11",
            confidence=Decimal("0.9000"),
            source_page_number=1,
        ),
        ProviderExtractedField(
            field_path="invoice.currency",
            value_type=ExtractionValueType.TEXT.value,
            raw_value="MYR",
            normalized_value="MYR",
            confidence=Decimal("0.9000"),
            source_page_number=1,
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type=ExtractionValueType.DECIMAL.value,
            raw_value=total,
            normalized_value=total,
            confidence=Decimal("0.9000"),
            source_page_number=1,
        ),
    ]
    if include_invoice_number:
        fields.append(
            ProviderExtractedField(
                field_path="invoice.number",
                value_type=ExtractionValueType.TEXT.value,
                raw_value=invoice_number,
                normalized_value=invoice_number,
                confidence=Decimal("0.9000"),
                source_page_number=1,
            )
        )
    if subtotal is not None:
        fields.append(
            ProviderExtractedField(
                field_path="invoice.subtotal",
                value_type=ExtractionValueType.DECIMAL.value,
                raw_value=subtotal,
                normalized_value=subtotal,
                confidence=Decimal("0.9000"),
                source_page_number=1,
            )
        )
    if tax is not None:
        fields.append(
            ProviderExtractedField(
                field_path="invoice.tax",
                value_type=ExtractionValueType.DECIMAL.value,
                raw_value=tax,
                normalized_value=tax,
                confidence=Decimal("0.9000"),
                source_page_number=1,
            )
        )
    return tuple(fields)
