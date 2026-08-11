from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ledgerpilot.api.app import create_app
from ledgerpilot.api.middleware import REQUEST_ID_HEADER
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.core.config import AuthMode, Environment, MalwareScannerMode, Settings
from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.documents.types import DocumentFailureCode, DocumentFileArea
from ledgerpilot.persistence.models.documents import Document, DocumentFile
from ledgerpilot.persistence.repositories.audit import AuditRepository
from ledgerpilot.persistence.repositories.documents import DocumentRepository
from ledgerpilot.storage.local import LocalDocumentStorage
from ledgerpilot.storage.protocol import StorageError
from tests.conftest import IdentitySeed

PDF_BYTES = b"%PDF-1.4\n% synthetic pdf for LedgerPilot tests\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\nsynthetic png for LedgerPilot tests"
JPEG_BYTES = b"\xff\xd8\xff\xe0synthetic jpeg for LedgerPilot tests"
MALWARE_MARKER = b"LEDGERPILOT_TEST_MALWARE"
SCANNER_ERROR_MARKER = b"LEDGERPILOT_TEST_SCANNER_ERROR"


class PromoteFailingStorage(LocalDocumentStorage):
    def promote(self, *, staged_key: str, accepted_key: str) -> None:
        raise StorageError("synthetic promote failure")


def _auth_headers(
    identity_seed: IdentitySeed,
    *,
    subject: str | None = None,
    firm_id: UUID | None = None,
    request_id: str = "req-document-test",
) -> dict[str, str]:
    return {
        "X-LedgerPilot-Dev-Subject": subject or identity_seed.accountant.external_subject,
        "X-LedgerPilot-Firm": str(firm_id or identity_seed.firm_a.id),
        REQUEST_ID_HEADER: request_id,
    }


def _upload(
    client: TestClient,
    *,
    client_id: UUID,
    filename: str,
    content: bytes,
    media_type: str,
    headers: dict[str, str],
):
    return client.post(
        f"/api/v1/clients/{client_id}/documents",
        headers=headers,
        files={"file": (filename, content, media_type)},
    )


def _storage_files(storage_root: Path) -> list[Path]:
    if not storage_root.exists():
        return []
    return [path for path in storage_root.rglob("*") if path.is_file()]


def _assert_no_storage_files(storage_root: Path) -> None:
    assert _storage_files(storage_root) == []


def _document_by_failure_code(
    db_session: Session,
    failure_code: DocumentFailureCode,
) -> Document:
    return db_session.scalars(
        select(Document).where(Document.failure_code == failure_code.value)
    ).one()


def _document_file_for_document(db_session: Session, document_id: UUID) -> DocumentFile:
    return db_session.scalars(
        select(DocumentFile).where(DocumentFile.document_id == document_id)
    ).one()


def test_authorised_accountant_uploads_valid_pdf_and_audit_event_is_recorded(
    client: TestClient,
    db_session: Session,
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename="synthetic-invoice.pdf",
        content=PDF_BYTES,
        media_type="application/pdf",
        headers=_auth_headers(identity_seed, request_id="req-upload-success"),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == DocumentStatus.STORED.value
    assert payload["submitted_filename"] == "synthetic-invoice.pdf"
    assert payload["media_type"] == "application/pdf"
    assert payload["size_bytes"] == len(PDF_BYTES)
    assert payload["sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()

    db_session.expire_all()
    document = DocumentRepository(db_session).get_document_for_client(
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
        document_id=UUID(payload["id"]),
    )
    assert document is not None
    assert document.submitted_by_user_id == identity_seed.accountant.id
    assert document.submitted_by_membership_id == identity_seed.accountant_membership.id
    document_file = _document_file_for_document(db_session, document.id)
    assert document_file.storage_area == DocumentFileArea.ACCEPTED.value
    assert "synthetic-invoice.pdf" not in document_file.storage_key
    assert document_storage.exists_accepted(document_file.storage_key)
    assert not document_storage.exists_staged(document_file.storage_key)
    with document_storage.open_for_processing(document_file.storage_key) as stored_file:
        assert stored_file.read() == PDF_BYTES

    events = [
        event
        for event in AuditRepository(db_session).list_for_firm(firm_id=identity_seed.firm_a.id)
        if event.target_id == str(document.id)
    ]
    assert {event.event_type for event in events} == {
        AuditEventType.DOCUMENT_INTAKE_STARTED.value,
        AuditEventType.DOCUMENT_STORED.value,
    }
    stored_event = next(
        event for event in events if event.event_type == AuditEventType.DOCUMENT_STORED.value
    )
    assert stored_event.firm_id == identity_seed.firm_a.id
    assert stored_event.client_id == identity_seed.client_a.id
    assert stored_event.actor_user_id == identity_seed.accountant.id
    assert stored_event.request_id == "req-upload-success"
    assert "storage_key" not in stored_event.metadata_json


@pytest.mark.parametrize(
    ("filename", "content", "media_type"),
    [
        ("synthetic-receipt.jpg", JPEG_BYTES, "image/jpeg"),
        ("synthetic-receipt.png", PNG_BYTES, "image/png"),
    ],
)
def test_authorised_upload_accepts_jpeg_and_png(
    client: TestClient,
    identity_seed: IdentitySeed,
    filename: str,
    content: bytes,
    media_type: str,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename=filename,
        content=content,
        media_type=media_type,
        headers=_auth_headers(identity_seed),
    )

    assert response.status_code == 201
    assert response.json()["status"] == DocumentStatus.STORED.value
    assert response.json()["media_type"] == media_type


def test_authorised_client_submitter_upload_succeeds(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename="submitter-upload.pdf",
        content=PDF_BYTES,
        media_type="application/pdf",
        headers=_auth_headers(
            identity_seed,
            subject=identity_seed.submitter.external_subject,
        ),
    )

    assert response.status_code == 201
    assert response.json()["status"] == DocumentStatus.STORED.value


def test_unauthenticated_upload_is_rejected_without_staging(
    client: TestClient,
    storage_root: Path,
    identity_seed: IdentitySeed,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename="unauthenticated.pdf",
        content=PDF_BYTES,
        media_type="application/pdf",
        headers={},
    )

    assert response.status_code == 401
    _assert_no_storage_files(storage_root)


def test_missing_client_access_upload_is_rejected_without_staging(
    client: TestClient,
    storage_root: Path,
    identity_seed: IdentitySeed,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_b.id,
        filename="client-b.pdf",
        content=PDF_BYTES,
        media_type="application/pdf",
        headers=_auth_headers(identity_seed),
    )

    assert response.status_code == 403
    _assert_no_storage_files(storage_root)


def test_cross_firm_upload_is_rejected_without_staging(
    client: TestClient,
    storage_root: Path,
    identity_seed: IdentitySeed,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.firm_b_client.id,
        filename="firm-b-client.pdf",
        content=PDF_BYTES,
        media_type="application/pdf",
        headers=_auth_headers(identity_seed),
    )

    assert response.status_code == 403
    _assert_no_storage_files(storage_root)


def test_document_metadata_lookup_respects_client_scope(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    upload_response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename="metadata.pdf",
        content=PDF_BYTES,
        media_type="application/pdf",
        headers=_auth_headers(identity_seed),
    )
    document_id = upload_response.json()["id"]

    allowed_response = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}",
        headers=_auth_headers(identity_seed),
    )
    denied_response = client.get(
        f"/api/v1/clients/{identity_seed.client_b.id}/documents/{document_id}",
        headers=_auth_headers(identity_seed),
    )

    assert allowed_response.status_code == 200
    assert "storage_key" not in allowed_response.text
    assert denied_response.status_code == 403


def test_empty_file_is_rejected_and_staging_is_cleaned(
    client: TestClient,
    db_session: Session,
    storage_root: Path,
    identity_seed: IdentitySeed,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename="empty.pdf",
        content=b"",
        media_type="application/pdf",
        headers=_auth_headers(identity_seed),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == DocumentFailureCode.EMPTY_FILE.value
    assert response.json()["error"]["request_id"] == response.headers[REQUEST_ID_HEADER]
    _assert_no_storage_files(storage_root)
    db_session.expire_all()
    document = _document_by_failure_code(db_session, DocumentFailureCode.EMPTY_FILE)
    assert document.status == DocumentStatus.VALIDATION_FAILED.value


def test_oversized_upload_is_rejected_while_streaming_and_partial_stage_is_cleaned(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    storage_root: Path,
    identity_seed: IdentitySeed,
) -> None:
    small_limit_settings = Settings(
        env=Environment.TEST,
        database_url=settings.database_url,
        auth_mode=AuthMode.DEVELOPMENT,
        dev_auth_enabled=True,
        document_max_bytes=8,
        document_storage_root=str(storage_root),
        malware_scanner_mode=MalwareScannerMode.DEVELOPMENT,
    )
    app = create_app(
        settings=small_limit_settings,
        session_factory=session_factory,
        document_storage=document_storage,
    )
    with TestClient(app) as test_client:
        response = _upload(
            test_client,
            client_id=identity_seed.client_a.id,
            filename="too-large.pdf",
            content=PDF_BYTES,
            media_type="application/pdf",
            headers=_auth_headers(identity_seed),
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == DocumentFailureCode.FILE_TOO_LARGE.value
    _assert_no_storage_files(storage_root)


@pytest.mark.parametrize(
    ("filename", "content", "media_type", "expected_code"),
    [
        ("unsupported.txt", b"plain text", "text/plain", DocumentFailureCode.UNSUPPORTED_FILE_TYPE),
        ("mismatch.pdf", PNG_BYTES, "application/pdf", DocumentFailureCode.CONTENT_TYPE_MISMATCH),
        (
            "wrong-extension.jpg",
            PDF_BYTES,
            "application/pdf",
            DocumentFailureCode.EXTENSION_MISMATCH,
        ),
    ],
)
def test_upload_validation_rejects_unsupported_mismatched_files_and_cleans_staging(
    client: TestClient,
    storage_root: Path,
    identity_seed: IdentitySeed,
    filename: str,
    content: bytes,
    media_type: str,
    expected_code: DocumentFailureCode,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename=filename,
        content=content,
        media_type=media_type,
        headers=_auth_headers(identity_seed),
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == expected_code.value
    _assert_no_storage_files(storage_root)


@pytest.mark.parametrize(
    "filename",
    [
        "../../secret.pdf",
        "..\\..\\secret.pdf",
        "folder/invoice.pdf",
        "folder\\invoice.pdf",
        "/tmp/invoice.pdf",
        "x" * 256 + ".pdf",
    ],
)
def test_path_like_or_dangerous_filenames_are_rejected_without_storage(
    client: TestClient,
    storage_root: Path,
    identity_seed: IdentitySeed,
    filename: str,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename=filename,
        content=PDF_BYTES,
        media_type="application/pdf",
        headers=_auth_headers(identity_seed),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == DocumentFailureCode.UNSAFE_FILENAME.value
    assert str(storage_root) not in response.text
    _assert_no_storage_files(storage_root)


def test_infected_file_is_quarantined_and_not_accepted(
    client: TestClient,
    db_session: Session,
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename="infected.pdf",
        content=PDF_BYTES + MALWARE_MARKER,
        media_type="application/pdf",
        headers=_auth_headers(identity_seed),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == DocumentFailureCode.MALWARE_DETECTED.value
    assert MALWARE_MARKER.decode() not in response.text

    db_session.expire_all()
    document = _document_by_failure_code(db_session, DocumentFailureCode.MALWARE_DETECTED)
    document_file = _document_file_for_document(db_session, document.id)
    assert document.status == DocumentStatus.QUARANTINED.value
    assert document_file.storage_area == DocumentFileArea.QUARANTINE.value
    assert document_storage.exists_quarantined(document_file.storage_key)
    assert not document_storage.exists_accepted(document_file.storage_key)


def test_scanner_error_fails_closed_and_is_quarantined_without_internal_details(
    client: TestClient,
    db_session: Session,
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    response = _upload(
        client,
        client_id=identity_seed.client_a.id,
        filename="scanner-error.pdf",
        content=PDF_BYTES + SCANNER_ERROR_MARKER,
        media_type="application/pdf",
        headers=_auth_headers(identity_seed),
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == DocumentFailureCode.MALWARE_SCAN_FAILED.value
    assert SCANNER_ERROR_MARKER.decode() not in response.text

    db_session.expire_all()
    document = _document_by_failure_code(db_session, DocumentFailureCode.MALWARE_SCAN_FAILED)
    document_file = _document_file_for_document(db_session, document.id)
    assert document.status == DocumentStatus.SCAN_FAILED.value
    assert document_file.storage_area == DocumentFileArea.QUARANTINE.value
    assert document_storage.exists_quarantined(document_file.storage_key)


def test_disabled_scanner_fails_closed(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    storage_root: Path,
    identity_seed: IdentitySeed,
) -> None:
    disabled_scanner_settings = Settings(
        env=Environment.TEST,
        database_url=settings.database_url,
        auth_mode=AuthMode.DEVELOPMENT,
        dev_auth_enabled=True,
        document_storage_root=str(storage_root),
        malware_scanner_mode=MalwareScannerMode.DISABLED,
    )
    app = create_app(
        settings=disabled_scanner_settings,
        session_factory=session_factory,
        document_storage=document_storage,
    )
    with TestClient(app) as test_client:
        response = _upload(
            test_client,
            client_id=identity_seed.client_a.id,
            filename="scanner-disabled.pdf",
            content=PDF_BYTES,
            media_type="application/pdf",
            headers=_auth_headers(identity_seed),
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == DocumentFailureCode.MALWARE_SCAN_FAILED.value


def test_storage_promotion_failure_cleans_staging_and_returns_safe_error(
    settings: Settings,
    session_factory: sessionmaker[Session],
    storage_root: Path,
    identity_seed: IdentitySeed,
) -> None:
    failing_storage = PromoteFailingStorage(storage_root)
    app = create_app(
        settings=settings,
        session_factory=session_factory,
        document_storage=failing_storage,
    )
    with TestClient(app) as test_client:
        response = _upload(
            test_client,
            client_id=identity_seed.client_a.id,
            filename="storage-failure.pdf",
            content=PDF_BYTES,
            media_type="application/pdf",
            headers=_auth_headers(identity_seed),
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == DocumentFailureCode.STORAGE_FAILED.value
    assert str(storage_root) not in response.text
    _assert_no_storage_files(storage_root)
