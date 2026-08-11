from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.service import AuditService
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.core.config import Settings
from ledgerpilot.documents.states import DocumentStatus, transition_document_status
from ledgerpilot.documents.types import DocumentFailureCode, DocumentFileArea
from ledgerpilot.documents.validation import (
    DOCUMENT_READ_CHUNK_BYTES,
    MAX_SIGNATURE_BYTES,
    DocumentValidationError,
    normalise_declared_media_type,
    validate_document_metadata,
    validate_submitted_filename,
)
from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.documents import Document, DocumentFile
from ledgerpilot.persistence.repositories.clients import ClientRepository
from ledgerpilot.persistence.repositories.documents import DocumentRepository
from ledgerpilot.scanning.protocol import MalwareScanner, MalwareScanResult, MalwareScanStatus
from ledgerpilot.storage.protocol import DocumentStorage, StorageError


@dataclass(frozen=True)
class StagedUploadResult:
    storage_key: str
    size_bytes: int
    sha256: str
    signature_bytes: bytes


class DocumentIntakeService:
    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        storage: DocumentStorage,
        scanner: MalwareScanner,
    ) -> None:
        self._session = session
        self._settings = settings
        self._storage = storage
        self._scanner = scanner
        self._clients = ClientRepository(session)
        self._documents = DocumentRepository(session)
        self._audit = AuditService(session)

    async def submit_document(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        upload_file: UploadFile,
        request_id: str | None,
    ) -> Document:
        self._require_client_access(principal=principal, client_id=client_id)

        try:
            submitted_filename = validate_submitted_filename(upload_file.filename)
        except DocumentValidationError as exc:
            self._record_pre_document_validation_failure(
                principal=principal,
                client_id=client_id,
                request_id=request_id,
                failure_code=exc.failure_code,
            )
            self._commit_without_storage()
            raise self._api_error(exc.failure_code) from exc

        document = Document(
            id=uuid.uuid4(),
            firm_id=principal.firm_id,
            client_id=client_id,
            submitted_by_user_id=principal.user_id,
            submitted_by_membership_id=principal.membership_id,
            status=DocumentStatus.UPLOADED.value,
            submitted_filename=submitted_filename,
        )
        self._documents.add_document(document)
        self._record_document_event(
            event_type=AuditEventType.DOCUMENT_INTAKE_STARTED,
            principal=principal,
            client_id=client_id,
            document_id=document.id,
            request_id=request_id,
        )

        staged_key: str | None = None
        accepted_key: str | None = None
        quarantine_key: str | None = None
        try:
            self._transition(document, DocumentStatus.VALIDATING)
            staged = await self._stage_upload(
                document=document,
                upload_file=upload_file,
            )
            staged_key = staged.storage_key

            declared_media_type = normalise_declared_media_type(upload_file.content_type)
            validation = validate_document_metadata(
                submitted_filename=submitted_filename,
                declared_media_type=declared_media_type,
                signature_bytes=staged.signature_bytes,
            )
            document.declared_media_type = validation.declared_media_type.value
            document.detected_media_type = validation.detected_media_type.value
            document.size_bytes = staged.size_bytes
            document.sha256 = staged.sha256

            self._transition(document, DocumentStatus.SCAN_PENDING)
            self._transition(document, DocumentStatus.SCANNING)
            scan_result = self._scan_staged_file(staged_key)
            if scan_result.status == MalwareScanStatus.CLEAN:
                accepted_key = self._new_storage_key(
                    firm_id=principal.firm_id,
                    client_id=client_id,
                    document_id=document.id,
                )
                self._storage.promote(staged_key=staged_key, accepted_key=accepted_key)
                staged_key = None
                self._transition(document, DocumentStatus.STORED)
                self._documents.add_document_file(
                    self._document_file(
                        document=document,
                        storage_area=DocumentFileArea.ACCEPTED,
                        storage_key=accepted_key,
                    )
                )
                self._record_document_event(
                    event_type=AuditEventType.DOCUMENT_STORED,
                    principal=principal,
                    client_id=client_id,
                    document_id=document.id,
                    request_id=request_id,
                    metadata={
                        "media_type": document.detected_media_type,
                        "size_bytes": document.size_bytes,
                        "sha256": document.sha256,
                    },
                )
                self._commit_with_storage_cleanup(accepted_key=accepted_key)
                return document

            quarantine_key = self._quarantine_staged_file(
                document=document,
                staged_key=staged_key,
                scan_result=scan_result,
                request_id=request_id,
            )
            staged_key = None
            self._documents.add_document_file(
                self._document_file(
                    document=document,
                    storage_area=DocumentFileArea.QUARANTINE,
                    storage_key=quarantine_key,
                )
            )
            self._commit_with_quarantine_cleanup(quarantine_key=quarantine_key)
            if document.status == DocumentStatus.QUARANTINED.value:
                raise self._api_error(DocumentFailureCode.MALWARE_DETECTED)
            raise self._api_error(DocumentFailureCode.MALWARE_SCAN_FAILED)
        except DocumentValidationError as exc:
            self._delete_staged_if_present(staged_key)
            self._mark_failure(document=document, failure_code=exc.failure_code)
            self._record_document_event(
                event_type=AuditEventType.DOCUMENT_VALIDATION_FAILED,
                principal=principal,
                client_id=client_id,
                document_id=document.id,
                request_id=request_id,
                metadata={"failure_code": exc.failure_code.value},
            )
            self._commit_without_storage()
            raise self._api_error(exc.failure_code) from exc
        except StorageError as exc:
            self._delete_staged_if_present(staged_key)
            self._delete_accepted_if_present(accepted_key)
            self._mark_failure(document=document, failure_code=DocumentFailureCode.STORAGE_FAILED)
            self._record_document_event(
                event_type=AuditEventType.DOCUMENT_SCAN_FAILED,
                principal=principal,
                client_id=client_id,
                document_id=document.id,
                request_id=request_id,
                metadata={"failure_code": DocumentFailureCode.STORAGE_FAILED.value},
            )
            self._commit_without_storage()
            raise self._api_error(DocumentFailureCode.STORAGE_FAILED) from exc
        except SQLAlchemyError:
            self._delete_staged_if_present(staged_key)
            self._delete_accepted_if_present(accepted_key)
            if quarantine_key is not None:
                self._storage.delete_quarantined(quarantine_key)
            raise

    def get_document_metadata(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
    ) -> Document:
        self._require_client_access(principal=principal, client_id=client_id)
        document = self._documents.get_document_for_client(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
        )
        if document is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return document

    def _require_client_access(self, *, principal: Principal, client_id: UUID) -> None:
        client = self._clients.get_authorized_client(
            membership_id=principal.membership_id,
            firm_id=principal.firm_id,
            client_id=client_id,
        )
        if client is None:
            raise ApiError(status_code=403, code="forbidden", message="Access denied.")

    async def _stage_upload(
        self,
        *,
        document: Document,
        upload_file: UploadFile,
    ) -> StagedUploadResult:
        storage_key = self._new_storage_key(
            firm_id=document.firm_id,
            client_id=document.client_id,
            document_id=document.id,
        )
        sha256 = hashlib.sha256()
        signature = bytearray()
        size_bytes = 0
        try:
            with self._storage.open_staged_writer(storage_key) as staged_file:
                while chunk := await upload_file.read(DOCUMENT_READ_CHUNK_BYTES):
                    size_bytes += len(chunk)
                    if size_bytes > self._settings.document_max_bytes:
                        raise DocumentValidationError(DocumentFailureCode.FILE_TOO_LARGE)
                    needed_signature_bytes = MAX_SIGNATURE_BYTES - len(signature)
                    if needed_signature_bytes > 0:
                        signature.extend(chunk[:needed_signature_bytes])
                    sha256.update(chunk)
                    staged_file.write(chunk)
        except Exception:
            self._delete_staged_if_present(storage_key)
            raise

        if size_bytes == 0:
            self._delete_staged_if_present(storage_key)
            raise DocumentValidationError(DocumentFailureCode.EMPTY_FILE)

        return StagedUploadResult(
            storage_key=storage_key,
            size_bytes=size_bytes,
            sha256=sha256.hexdigest(),
            signature_bytes=bytes(signature),
        )

    def _scan_staged_file(self, staged_key: str) -> MalwareScanResult:
        try:
            return self._scanner.scan_staged(storage=self._storage, storage_key=staged_key)
        except Exception:
            return MalwareScanResult(
                status=MalwareScanStatus.ERROR,
                safe_code="scanner_failed",
            )

    def _quarantine_staged_file(
        self,
        *,
        document: Document,
        staged_key: str,
        scan_result: MalwareScanResult,
        request_id: str | None,
    ) -> str:
        quarantine_key = self._new_storage_key(
            firm_id=document.firm_id,
            client_id=document.client_id,
            document_id=document.id,
        )
        self._storage.quarantine(staged_key=staged_key, quarantine_key=quarantine_key)
        if scan_result.status == MalwareScanStatus.INFECTED:
            self._transition(document, DocumentStatus.QUARANTINED)
            document.failure_code = DocumentFailureCode.MALWARE_DETECTED.value
            event_type = AuditEventType.DOCUMENT_QUARANTINED
            failure_code = DocumentFailureCode.MALWARE_DETECTED
        else:
            self._transition(document, DocumentStatus.SCAN_FAILED)
            document.failure_code = DocumentFailureCode.MALWARE_SCAN_FAILED.value
            event_type = AuditEventType.DOCUMENT_SCAN_FAILED
            failure_code = DocumentFailureCode.MALWARE_SCAN_FAILED

        self._record_document_event(
            event_type=event_type,
            principal_user_id=document.submitted_by_user_id,
            firm_id=document.firm_id,
            client_id=document.client_id,
            document_id=document.id,
            request_id=request_id,
            metadata={"failure_code": failure_code.value},
        )
        return quarantine_key

    def _document_file(
        self,
        *,
        document: Document,
        storage_area: DocumentFileArea,
        storage_key: str,
    ) -> DocumentFile:
        if document.size_bytes is None or document.sha256 is None:
            raise ValueError("document file metadata requires size and sha256")
        return DocumentFile(
            document_id=document.id,
            firm_id=document.firm_id,
            client_id=document.client_id,
            storage_backend=self._storage.backend_name,
            storage_area=storage_area.value,
            storage_key=storage_key,
            size_bytes=document.size_bytes,
            sha256=document.sha256,
        )

    def _mark_failure(self, *, document: Document, failure_code: DocumentFailureCode) -> None:
        current_status = DocumentStatus(document.status)
        failure_status = (
            DocumentStatus.SCAN_FAILED
            if current_status in {DocumentStatus.SCAN_PENDING, DocumentStatus.SCANNING}
            else DocumentStatus.VALIDATION_FAILED
        )
        if (
            failure_status
            in {
                DocumentStatus.VALIDATION_FAILED,
                DocumentStatus.SCAN_FAILED,
            }
            and current_status != failure_status
        ):
            self._transition(document, failure_status)
        document.failure_code = failure_code.value

    def _transition(self, document: Document, status: DocumentStatus) -> None:
        current_status = DocumentStatus(document.status)
        document.status = transition_document_status(current_status, status).value

    def _record_pre_document_validation_failure(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        request_id: str | None,
        failure_code: DocumentFailureCode,
    ) -> None:
        self._audit.record_event(
            firm_id=principal.firm_id,
            client_id=client_id,
            actor_user_id=principal.user_id,
            event_type=AuditEventType.DOCUMENT_VALIDATION_FAILED.value,
            target_type="document_intake",
            target_id="uncreated",
            request_id=request_id,
            metadata={"failure_code": failure_code.value},
        )

    def _record_document_event(
        self,
        *,
        event_type: AuditEventType,
        client_id: UUID,
        document_id: UUID,
        request_id: str | None,
        principal: Principal | None = None,
        principal_user_id: UUID | None = None,
        firm_id: UUID | None = None,
        metadata: dict[str, object | None] | None = None,
    ) -> None:
        actor_user_id = principal.user_id if principal is not None else principal_user_id
        event_firm_id = principal.firm_id if principal is not None else firm_id
        if actor_user_id is None or event_firm_id is None:
            raise ValueError("audit event requires actor and firm")
        self._audit.record_event(
            firm_id=event_firm_id,
            client_id=client_id,
            actor_user_id=actor_user_id,
            event_type=event_type.value,
            target_type="document",
            target_id=str(document_id),
            request_id=request_id,
            metadata=metadata,
        )

    def _commit_without_storage(self) -> None:
        self._session.commit()

    def _commit_with_storage_cleanup(self, *, accepted_key: str) -> None:
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._delete_accepted_if_present(accepted_key)
            raise

    def _commit_with_quarantine_cleanup(self, *, quarantine_key: str) -> None:
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._storage.delete_quarantined(quarantine_key)
            raise

    def _delete_staged_if_present(self, storage_key: str | None) -> None:
        if storage_key is not None:
            self._storage.delete_staged(storage_key)

    def _delete_accepted_if_present(self, storage_key: str | None) -> None:
        if storage_key is not None:
            self._storage.delete_accepted(storage_key)

    def _new_storage_key(self, *, firm_id: UUID, client_id: UUID, document_id: UUID) -> str:
        return f"{firm_id}/{client_id}/{document_id}/{uuid.uuid4().hex}"

    def _api_error(self, failure_code: DocumentFailureCode) -> ApiError:
        status_code = {
            DocumentFailureCode.EMPTY_FILE: 400,
            DocumentFailureCode.FILE_TOO_LARGE: 413,
            DocumentFailureCode.UNSUPPORTED_FILE_TYPE: 415,
            DocumentFailureCode.CONTENT_TYPE_MISMATCH: 415,
            DocumentFailureCode.EXTENSION_MISMATCH: 415,
            DocumentFailureCode.UNSAFE_FILENAME: 400,
            DocumentFailureCode.MALWARE_DETECTED: 400,
            DocumentFailureCode.MALWARE_SCAN_FAILED: 503,
            DocumentFailureCode.STORAGE_FAILED: 503,
        }[failure_code]
        message = {
            DocumentFailureCode.MALWARE_DETECTED: "Document was rejected.",
            DocumentFailureCode.MALWARE_SCAN_FAILED: "Document could not be scanned.",
            DocumentFailureCode.STORAGE_FAILED: "Document could not be stored.",
        }.get(failure_code, "Document upload rejected.")
        return ApiError(status_code=status_code, code=failure_code.value, message=message)
