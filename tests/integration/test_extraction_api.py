from __future__ import annotations

import hashlib
import uuid
from decimal import Decimal
from typing import BinaryIO
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ledgerpilot.api.app import create_app
from ledgerpilot.api.middleware import REQUEST_ID_HEADER
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.core.config import Settings
from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.extraction.development import DevelopmentExtractionProvider
from ledgerpilot.extraction.protocol import ExtractionRequestContext
from ledgerpilot.extraction.types import (
    ExtractionProviderMetadata,
    ExtractionProviderResult,
    ProviderExtractedField,
)
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.documents import Document, DocumentFile
from ledgerpilot.persistence.models.extraction import (
    ExtractedField,
    ExtractionFieldCorrection,
    ExtractionRun,
)
from ledgerpilot.persistence.repositories.audit import AuditRepository
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from ledgerpilot.storage.local import LocalDocumentStorage
from tests.conftest import IdentitySeed

PDF_BYTES = b"%PDF-1.4\n% synthetic pdf for LedgerPilot Phase 3 extraction tests\n"


class FailingExtractionProvider:
    @property
    def metadata(self) -> ExtractionProviderMetadata:
        return ExtractionProviderMetadata(
            provider_name="synthetic_failing_provider",
            provider_version="0.1.0",
            model_version="synthetic-error-model",
            extraction_schema_version="ledgerpilot.extraction.v1",
        )

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        del source_file, context
        raise RuntimeError("synthetic provider exception with filesystem /private/tmp/leak")


class InvalidExtractionProvider:
    @property
    def metadata(self) -> ExtractionProviderMetadata:
        return ExtractionProviderMetadata(
            provider_name="synthetic_invalid_provider",
            provider_version="0.1.0",
            model_version=None,
            extraction_schema_version="ledgerpilot.extraction.v1",
        )

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        del source_file, context
        return ExtractionProviderResult(
            metadata=self.metadata,
            fields=(
                ProviderExtractedField(
                    field_path="firm_id",
                    value_type="text",
                    raw_value=str(uuid.uuid4()),
                ),
            ),
        )


class LineageMismatchExtractionProvider:
    @property
    def metadata(self) -> ExtractionProviderMetadata:
        return ExtractionProviderMetadata(
            provider_name="synthetic_lineage_provider",
            provider_version="0.1.0",
            model_version="synthetic-model-a",
            extraction_schema_version="ledgerpilot.extraction.v1",
        )

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        del source_file, context
        return ExtractionProviderResult(
            metadata=ExtractionProviderMetadata(
                provider_name="synthetic_lineage_provider",
                provider_version="0.2.0",
                model_version="synthetic-model-b",
                extraction_schema_version="ledgerpilot.extraction.v2",
            ),
            fields=(
                ProviderExtractedField(
                    field_path="invoice.number",
                    value_type="text",
                    raw_value="SYN-LINEAGE-001",
                ),
            ),
        )


class NonFiniteExtractionProvider:
    @property
    def metadata(self) -> ExtractionProviderMetadata:
        return ExtractionProviderMetadata(
            provider_name="synthetic_non_finite_provider",
            provider_version="0.1.0",
            model_version=None,
            extraction_schema_version="ledgerpilot.extraction.v1",
        )

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        del source_file, context
        return ExtractionProviderResult(
            metadata=self.metadata,
            fields=(
                ProviderExtractedField(
                    field_path="invoice.total",
                    value_type="decimal",
                    raw_value="RM NaN",
                    normalized_value="NaN",
                    confidence=Decimal("NaN"),
                    source_page_number=1,
                    source_locator={"bbox": {"x1": "0", "y1": "0", "x2": "1", "y2": "1"}},
                ),
            ),
        )


class SparseExtractionProvider:
    @property
    def metadata(self) -> ExtractionProviderMetadata:
        return ExtractionProviderMetadata(
            provider_name="synthetic_sparse_provider",
            provider_version="0.2.0",
            model_version=None,
            extraction_schema_version="ledgerpilot.extraction.v1",
        )

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        del source_file, context
        return ExtractionProviderResult(
            metadata=self.metadata,
            fields=(
                ProviderExtractedField(
                    field_path="invoice.number",
                    value_type="text",
                    raw_value="SYN-LOW-001",
                    confidence=Decimal("0.1200"),
                    source_page_number=1,
                ),
                ProviderExtractedField(
                    field_path="invoice.notes",
                    value_type="text",
                    raw_value="Synthetic provider did not supply calibrated confidence.",
                    confidence=None,
                    source_page_number=1,
                ),
            ),
        )


class CommitFailingSession(Session):
    commit_attempts = 0
    rollback_called = False

    def commit(self) -> None:
        CommitFailingSession.commit_attempts += 1
        raise SQLAlchemyError("synthetic extraction persistence failure")

    def rollback(self) -> None:
        CommitFailingSession.rollback_called = True
        super().rollback()


def _auth_headers(
    identity_seed: IdentitySeed,
    *,
    subject: str | None = None,
    firm_id: UUID | None = None,
    request_id: str = "req-extraction-test",
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
    filename: str = "synthetic-extraction-source.pdf",
) -> UUID:
    response = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents",
        headers=_auth_headers(identity_seed),
        files={"file": (filename, PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _start_extraction(
    client: TestClient,
    identity_seed: IdentitySeed,
    *,
    document_id: UUID,
    client_id: UUID | None = None,
    subject: str | None = None,
    request_id: str = "req-extraction-start",
):
    target_client_id = client_id or identity_seed.client_a.id
    return client.post(
        f"/api/v1/clients/{target_client_id}/documents/{document_id}/extractions",
        headers=_auth_headers(identity_seed, subject=subject, request_id=request_id),
    )


def _create_app_with_provider(
    *,
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    provider: object,
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
    senior = repository.add_user(external_subject="dev-senior")
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


def _direct_document(
    db_session: Session,
    identity_seed: IdentitySeed,
    *,
    status: DocumentStatus,
) -> Document:
    document = Document(
        id=uuid.uuid4(),
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
        submitted_by_user_id=identity_seed.accountant.id,
        submitted_by_membership_id=identity_seed.accountant_membership.id,
        status=status.value,
        submitted_filename=f"synthetic-{status.value}.pdf",
        declared_media_type="application/pdf",
        detected_media_type="application/pdf",
        size_bytes=len(PDF_BYTES),
        sha256=hashlib.sha256(PDF_BYTES).hexdigest(),
    )
    db_session.add(document)
    db_session.commit()
    return document


def test_accountant_runs_extraction_for_stored_accepted_document(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)

    response = _start_extraction(client, identity_seed, document_id=document_id)

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["provider_name"] == "development"
    assert payload["provider_version"] == "0.1.0"
    assert payload["extraction_schema_version"] == "ledgerpilot.extraction.v1"
    assert payload["source_sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()
    assert payload["downstream_ready"] is True
    assert {field["field_path"] for field in payload["fields"]} >= {
        "document.type",
        "supplier.name",
        "invoice.number",
        "invoice.total",
    }
    total = next(field for field in payload["fields"] if field["field_path"] == "invoice.total")
    assert total["original_raw_value"] == "RM 100.00"
    assert total["original_normalized_value"] == "100.00"
    assert total["confidence"] == "0.7100"
    assert total["corrected"] is False

    run = db_session.get(ExtractionRun, UUID(payload["id"]))
    assert run is not None
    assert run.source_sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
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
        AuditEventType.EXTRACTION_STARTED.value,
        AuditEventType.EXTRACTION_SUCCEEDED.value,
    }
    for event in events:
        assert event.client_id == identity_seed.client_a.id
        assert event.actor_user_id == identity_seed.accountant.id
        assert "RM 100.00" not in str(event.metadata_json)
        assert "storage_key" not in event.metadata_json


def test_senior_reviewer_can_run_extraction(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    senior_subject = _add_senior_reviewer(db_session, identity_seed)
    document_id = _upload_document(client, identity_seed)

    response = _start_extraction(
        client,
        identity_seed,
        document_id=document_id,
        subject=senior_subject,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "succeeded"


def test_users_without_run_extraction_permission_are_denied(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)

    for subject in (
        identity_seed.submitter.external_subject,
        identity_seed.auditor.external_subject,
        identity_seed.admin.external_subject,
    ):
        response = _start_extraction(
            client,
            identity_seed,
            document_id=document_id,
            subject=subject,
        )
        assert response.status_code == 403


def test_cross_client_and_cross_firm_extraction_are_denied(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)

    cross_client = _start_extraction(
        client,
        identity_seed,
        client_id=identity_seed.client_b.id,
        document_id=document_id,
    )
    cross_firm = _start_extraction(
        client,
        identity_seed,
        client_id=identity_seed.firm_b_client.id,
        document_id=document_id,
    )

    assert cross_client.status_code == 403
    assert cross_firm.status_code == 403


def test_non_stored_document_states_are_not_eligible_for_extraction(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    for status in (
        DocumentStatus.UPLOADED,
        DocumentStatus.VALIDATING,
        DocumentStatus.VALIDATION_FAILED,
        DocumentStatus.SCAN_PENDING,
        DocumentStatus.SCANNING,
        DocumentStatus.SCAN_FAILED,
        DocumentStatus.QUARANTINED,
        DocumentStatus.REJECTED,
    ):
        document = _direct_document(db_session, identity_seed, status=status)

        response = _start_extraction(client, identity_seed, document_id=document.id)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "source_not_eligible"


def test_stored_document_without_accepted_file_is_not_eligible(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document = _direct_document(db_session, identity_seed, status=DocumentStatus.STORED)

    response = _start_extraction(client, identity_seed, document_id=document.id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "source_file_missing"


def test_missing_storage_object_creates_failed_run_without_path_leak(
    client: TestClient,
    db_session: Session,
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    document_file = db_session.scalars(
        select(DocumentFile).where(DocumentFile.document_id == document_id)
    ).one()
    document_storage.delete_accepted(document_file.storage_key)

    response = _start_extraction(client, identity_seed, document_id=document_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "source_file_missing"
    assert str(document_storage.root) not in response.text
    run = db_session.scalars(
        select(ExtractionRun).where(ExtractionRun.document_id == document_id)
    ).one()
    assert run.status == "failed"
    assert run.failure_code == "source_file_missing"


def test_provider_exception_creates_failed_run_and_safe_error(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    with _create_app_with_provider(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        provider=FailingExtractionProvider(),
    ) as failing_client:
        document_id = _upload_document(failing_client, identity_seed)
        response = _start_extraction(failing_client, identity_seed, document_id=document_id)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_failed"
    assert "synthetic provider exception" not in response.text
    assert "/private/tmp" not in response.text
    run = db_session.scalars(
        select(ExtractionRun).where(ExtractionRun.document_id == document_id)
    ).one()
    assert run.status == "failed"
    assert run.failure_code == "provider_failed"
    assert (
        db_session.scalars(
            select(ExtractedField).where(ExtractedField.extraction_run_id == run.id)
        ).all()
        == []
    )


def test_invalid_provider_output_fails_without_partial_fields(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    with _create_app_with_provider(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        provider=InvalidExtractionProvider(),
    ) as invalid_client:
        document_id = _upload_document(invalid_client, identity_seed)
        response = _start_extraction(invalid_client, identity_seed, document_id=document_id)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_provider_output"
    run = db_session.scalars(
        select(ExtractionRun).where(ExtractionRun.document_id == document_id)
    ).one()
    assert run.status == "failed"
    assert run.failure_code == "invalid_provider_output"
    assert (
        db_session.scalars(
            select(ExtractedField).where(ExtractedField.extraction_run_id == run.id)
        ).all()
        == []
    )


def test_provider_lineage_mismatch_fails_without_successful_fields(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    with _create_app_with_provider(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        provider=LineageMismatchExtractionProvider(),
    ) as invalid_client:
        document_id = _upload_document(invalid_client, identity_seed)
        response = _start_extraction(invalid_client, identity_seed, document_id=document_id)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_provider_output"
    run = db_session.scalars(
        select(ExtractionRun).where(ExtractionRun.document_id == document_id)
    ).one()
    assert run.status == "failed"
    assert run.failure_code == "invalid_provider_output"
    assert run.provider_name == "synthetic_lineage_provider"
    assert run.provider_version == "0.1.0"
    assert (
        db_session.scalars(
            select(ExtractedField).where(ExtractedField.extraction_run_id == run.id)
        ).all()
        == []
    )


def test_non_finite_provider_output_is_invalid_output_not_provider_failure(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    with _create_app_with_provider(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        provider=NonFiniteExtractionProvider(),
    ) as invalid_client:
        document_id = _upload_document(invalid_client, identity_seed)
        response = _start_extraction(invalid_client, identity_seed, document_id=document_id)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_provider_output"
    assert "provider_failed" not in response.text
    run = db_session.scalars(
        select(ExtractionRun).where(ExtractionRun.document_id == document_id)
    ).one()
    assert run.status == "failed"
    assert run.failure_code == "invalid_provider_output"
    assert (
        db_session.scalars(
            select(ExtractedField).where(ExtractedField.extraction_run_id == run.id)
        ).all()
        == []
    )


def test_extraction_commit_failure_rolls_back_without_provider_failure(
    client: TestClient,
    settings: Settings,
    engine: Engine,
    document_storage: LocalDocumentStorage,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    failing_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        class_=CommitFailingSession,
    )
    CommitFailingSession.commit_attempts = 0
    CommitFailingSession.rollback_called = False

    with _create_app_with_provider(
        settings=settings,
        session_factory=failing_session_factory,
        document_storage=document_storage,
        provider=DevelopmentExtractionProvider(
            extraction_schema_version=settings.extraction_schema_version,
        ),
    ) as failing_client:
        response = _start_extraction(failing_client, identity_seed, document_id=document_id)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "persistence_failed"
    assert "provider_failed" not in response.text
    assert CommitFailingSession.commit_attempts == 1
    assert CommitFailingSession.rollback_called is True
    assert (
        db_session.scalars(
            select(ExtractionRun).where(ExtractionRun.document_id == document_id)
        ).all()
        == []
    )
    assert (
        db_session.scalars(
            select(ExtractedField).where(ExtractedField.document_id == document_id)
        ).all()
        == []
    )


def test_low_and_missing_confidence_remain_visible(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    with _create_app_with_provider(
        settings=settings,
        session_factory=session_factory,
        document_storage=document_storage,
        provider=SparseExtractionProvider(),
    ) as sparse_client:
        document_id = _upload_document(sparse_client, identity_seed)
        response = _start_extraction(sparse_client, identity_seed, document_id=document_id)

    assert response.status_code == 201
    fields = {field["field_path"]: field for field in response.json()["fields"]}
    assert fields["invoice.number"]["confidence"] == "0.1200"
    assert fields["invoice.notes"]["confidence"] is None


def test_multiple_extraction_attempts_create_distinct_runs(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)

    first = _start_extraction(client, identity_seed, document_id=document_id)
    second = _start_extraction(client, identity_seed, document_id=document_id)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_metadata_lookup_respects_scope_and_lists_history(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    run_response = _start_extraction(client, identity_seed, document_id=document_id)
    run_id = run_response.json()["id"]

    allowed = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/{run_id}",
        headers=_auth_headers(identity_seed),
    )
    list_response = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions",
        headers=_auth_headers(identity_seed),
    )
    denied = client.get(
        f"/api/v1/clients/{identity_seed.client_b.id}/documents/{document_id}/extractions/{run_id}",
        headers=_auth_headers(identity_seed),
    )

    assert allowed.status_code == 200
    assert allowed.json()["id"] == run_id
    assert list_response.status_code == 200
    assert [run["id"] for run in list_response.json()] == [run_id]
    assert denied.status_code == 403


def test_accountant_correction_preserves_original_and_latest_effective_value(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    run_payload = _start_extraction(client, identity_seed, document_id=document_id).json()
    field = next(field for field in run_payload["fields"] if field["field_path"] == "invoice.total")

    first = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/"
        f"{run_payload['id']}/fields/{field['id']}/corrections",
        headers=_auth_headers(identity_seed, request_id="req-correction-1"),
        json={
            "corrected_raw_value": "RM 100.00",
            "corrected_normalized_value": "100.00",
            "corrected_value_type": "decimal",
            "reason": "Synthetic correction for OCR decimal candidate.",
        },
    )
    second = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/"
        f"{run_payload['id']}/fields/{field['id']}/corrections",
        headers=_auth_headers(identity_seed, request_id="req-correction-2"),
        json={
            "corrected_raw_value": "RM 101.00",
            "corrected_normalized_value": "101.00",
            "corrected_value_type": "decimal",
            "reason": "Synthetic second correction.",
        },
    )

    assert first.status_code == 201
    assert first.json()["original_raw_value"] == "RM 100.00"
    assert first.json()["effective_normalized_value"] == "100.00"
    assert first.json()["confidence"] == field["confidence"]
    assert first.json()["latest_revision_number"] == 1
    assert second.status_code == 201
    assert second.json()["original_raw_value"] == "RM 100.00"
    assert second.json()["effective_normalized_value"] == "101.00"
    assert second.json()["confidence"] == field["confidence"]
    assert second.json()["latest_revision_number"] == 2

    stored_field = db_session.get(ExtractedField, UUID(field["id"]))
    assert stored_field is not None
    assert stored_field.raw_value == "RM 100.00"
    corrections = db_session.scalars(
        select(ExtractionFieldCorrection).where(
            ExtractionFieldCorrection.field_id == UUID(field["id"])
        )
    ).all()
    assert [correction.revision_number for correction in corrections] == [1, 2]
    assert {correction.corrected_by_user_id for correction in corrections} == {
        identity_seed.accountant.id
    }

    correction_events = [
        event
        for event in AuditRepository(db_session).list_for_firm(firm_id=identity_seed.firm_a.id)
        if event.event_type == AuditEventType.EXTRACTION_CORRECTION_RECORDED.value
    ]
    assert len(correction_events) == 2
    for event in correction_events:
        assert "RM 101.00" not in str(event.metadata_json)
        assert "corrected_raw_value" not in event.metadata_json


def test_senior_reviewer_can_correct_extracted_field(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    senior_subject = _add_senior_reviewer(db_session, identity_seed)
    document_id = _upload_document(client, identity_seed)
    run_payload = _start_extraction(client, identity_seed, document_id=document_id).json()
    field = next(
        field for field in run_payload["fields"] if field["field_path"] == "invoice.number"
    )

    response = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/"
        f"{run_payload['id']}/fields/{field['id']}/corrections",
        headers=_auth_headers(identity_seed, subject=senior_subject),
        json={
            "corrected_raw_value": "SYN-INV-001-A",
            "corrected_normalized_value": "SYN-INV-001-A",
            "corrected_value_type": "text",
            "reason": "Synthetic senior correction.",
        },
    )

    assert response.status_code == 201
    assert response.json()["corrected"] is True


def test_submitter_and_auditor_cannot_correct_extracted_field(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    run_payload = _start_extraction(client, identity_seed, document_id=document_id).json()
    field = run_payload["fields"][0]

    for subject in (
        identity_seed.submitter.external_subject,
        identity_seed.auditor.external_subject,
    ):
        response = client.post(
            f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/"
            f"{run_payload['id']}/fields/{field['id']}/corrections",
            headers=_auth_headers(identity_seed, subject=subject),
            json={
                "corrected_raw_value": "Synthetic correction",
                "corrected_normalized_value": "Synthetic correction",
                "corrected_value_type": "text",
                "reason": "Synthetic correction attempt.",
            },
        )
        assert response.status_code == 403


def test_correction_reason_and_value_validation(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed)
    run_payload = _start_extraction(client, identity_seed, document_id=document_id).json()
    field = next(field for field in run_payload["fields"] if field["field_path"] == "invoice.total")

    missing_reason = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/"
        f"{run_payload['id']}/fields/{field['id']}/corrections",
        headers=_auth_headers(identity_seed),
        json={
            "corrected_raw_value": "RM 100.00",
            "corrected_normalized_value": "100.00",
            "corrected_value_type": "decimal",
            "reason": "",
        },
    )
    invalid_decimal = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/"
        f"{run_payload['id']}/fields/{field['id']}/corrections",
        headers=_auth_headers(identity_seed),
        json={
            "corrected_raw_value": "RM 100.00",
            "corrected_normalized_value": "not-a-decimal",
            "corrected_value_type": "decimal",
            "reason": "Synthetic invalid decimal.",
        },
    )

    assert missing_reason.status_code == 422
    assert invalid_decimal.status_code == 422
    assert invalid_decimal.json()["error"]["code"] == "invalid_correction"
