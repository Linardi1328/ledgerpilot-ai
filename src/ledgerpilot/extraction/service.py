from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.service import AuditService
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.core.config import Settings
from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.documents.types import DocumentFileArea
from ledgerpilot.extraction.protocol import ExtractionProvider, ExtractionRequestContext
from ledgerpilot.extraction.states import ExtractionRunStatus, transition_extraction_status
from ledgerpilot.extraction.types import (
    ExtractionFailureCode,
    ExtractionProviderMetadata,
    ExtractionProviderResult,
    ProviderExtractedField,
)
from ledgerpilot.extraction.validation import (
    ProviderOutputValidationError,
    validate_provider_field,
    validate_provider_lineage,
    validate_provider_result,
)
from ledgerpilot.identity.principal import Principal
from ledgerpilot.persistence.models.documents import DocumentFile
from ledgerpilot.persistence.models.extraction import (
    ExtractedField,
    ExtractionFieldCorrection,
    ExtractionRun,
)
from ledgerpilot.persistence.repositories.clients import ClientRepository
from ledgerpilot.persistence.repositories.documents import DocumentRepository
from ledgerpilot.persistence.repositories.extraction import ExtractionRepository
from ledgerpilot.storage.protocol import DocumentStorage, StorageError

logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        storage: DocumentStorage,
        provider: ExtractionProvider,
    ) -> None:
        self._session = session
        self._settings = settings
        self._storage = storage
        self._provider = provider
        self._clients = ClientRepository(session)
        self._documents = DocumentRepository(session)
        self._extractions = ExtractionRepository(session)
        self._audit = AuditService(session)

    def start_extraction(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        request_id: str | None,
    ) -> ExtractionRun:
        self._require_client_access(principal=principal, client_id=client_id)
        document = self._documents.get_document_for_client(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
        )
        if document is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        if document.status != DocumentStatus.STORED.value:
            raise ApiError(
                status_code=409,
                code=ExtractionFailureCode.SOURCE_NOT_ELIGIBLE.value,
                message="Document is not eligible for extraction.",
            )
        document_file = self._documents.get_accepted_document_file_for_client(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
        )
        if document_file is None or document_file.storage_area != DocumentFileArea.ACCEPTED.value:
            raise ApiError(
                status_code=409,
                code=ExtractionFailureCode.SOURCE_FILE_MISSING.value,
                message="Document source file is not available for extraction.",
            )
        if self._provider.metadata.provider_name == "disabled":
            raise ApiError(
                status_code=503,
                code=ExtractionFailureCode.PROVIDER_DISABLED.value,
                message="Extraction provider is not configured.",
            )

        run = self._new_run(
            principal=principal,
            document_file=document_file,
            request_id=request_id,
        )
        self._extractions.add_run(run)
        self._transition(run, ExtractionRunStatus.RUNNING)
        self._record_extraction_event(
            event_type=AuditEventType.EXTRACTION_STARTED,
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
            provider_result = self._run_provider(
                document_file=document_file,
                run=run,
                media_type=document.detected_media_type or "application/octet-stream",
            )
        except StorageError as exc:
            self._fail_run_and_commit(
                run=run,
                principal=principal,
                client_id=client_id,
                request_id=request_id,
                failure_code=ExtractionFailureCode.SOURCE_FILE_MISSING,
            )
            logger.info(
                "Extraction source file was unavailable",
                extra={
                    "request_id": request_id,
                    "run_id": str(run.id),
                    "failure_code": ExtractionFailureCode.SOURCE_FILE_MISSING.value,
                    "exception_type": type(exc).__name__,
                },
            )
            self._session.commit()
            raise ApiError(
                status_code=409,
                code=ExtractionFailureCode.SOURCE_FILE_MISSING.value,
                message="Document source file is not available for extraction.",
            ) from exc
        except Exception as exc:
            self._fail_run_and_commit(
                run=run,
                principal=principal,
                client_id=client_id,
                request_id=request_id,
                failure_code=ExtractionFailureCode.PROVIDER_FAILED,
            )
            logger.info(
                "Extraction provider failed",
                extra={
                    "request_id": request_id,
                    "run_id": str(run.id),
                    "failure_code": ExtractionFailureCode.PROVIDER_FAILED.value,
                    "exception_type": type(exc).__name__,
                },
            )
            self._session.commit()
            raise ApiError(
                status_code=503,
                code=ExtractionFailureCode.PROVIDER_FAILED.value,
                message="Extraction provider failed.",
            ) from exc

        try:
            validate_provider_lineage(
                result_metadata=provider_result.metadata,
                expected_metadata=_run_metadata(run),
            )
            validated_fields = validate_provider_result(
                provider_result,
                max_fields=self._settings.extraction_max_fields,
                max_value_chars=self._settings.extraction_max_value_chars,
            )
        except ProviderOutputValidationError as exc:
            self._fail_run_and_commit(
                run=run,
                principal=principal,
                client_id=client_id,
                request_id=request_id,
                failure_code=ExtractionFailureCode.INVALID_PROVIDER_OUTPUT,
            )
            logger.info(
                "Extraction provider output rejected",
                extra={
                    "request_id": request_id,
                    "run_id": str(run.id),
                    "failure_code": ExtractionFailureCode.INVALID_PROVIDER_OUTPUT.value,
                },
            )
            raise ApiError(
                status_code=422,
                code=ExtractionFailureCode.INVALID_PROVIDER_OUTPUT.value,
                message="Extraction output was rejected.",
            ) from exc

        for field in validated_fields:
            self._extractions.add_field(
                ExtractedField(
                    extraction_run_id=run.id,
                    firm_id=run.firm_id,
                    client_id=run.client_id,
                    document_id=run.document_id,
                    field_path=field.field_path,
                    value_type=field.value_type.value,
                    raw_value=field.raw_value,
                    normalized_value=field.normalized_value,
                    confidence=field.confidence,
                    source_page_number=field.source_page_number,
                    source_locator=field.source_locator,
                )
            )
        self._transition(run, ExtractionRunStatus.SUCCEEDED)
        self._record_extraction_event(
            event_type=AuditEventType.EXTRACTION_SUCCEEDED,
            principal=principal,
            client_id=client_id,
            run=run,
            request_id=request_id,
            metadata={**_run_event_metadata(run), "field_count": len(validated_fields)},
        )
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._raise_persistence_error(run=run, request_id=request_id, exc=exc)
        return run

    def get_extraction_run(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        run_id: UUID,
    ) -> tuple[ExtractionRun, list[ExtractedField], list[ExtractionFieldCorrection]]:
        self._require_client_access(principal=principal, client_id=client_id)
        run = self._extractions.get_run_for_document(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            run_id=run_id,
        )
        if run is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        fields = self._extractions.list_fields_for_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            run_id=run_id,
        )
        corrections = self._extractions.list_corrections_for_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            run_id=run_id,
        )
        return run, fields, corrections

    def list_extraction_runs(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
    ) -> list[ExtractionRun]:
        self._require_client_access(principal=principal, client_id=client_id)
        if (
            self._documents.get_document_for_client(
                firm_id=principal.firm_id,
                client_id=client_id,
                document_id=document_id,
            )
            is None
        ):
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        return self._extractions.list_runs_for_document(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
        )

    def correct_field(
        self,
        *,
        principal: Principal,
        client_id: UUID,
        document_id: UUID,
        run_id: UUID,
        field_id: UUID,
        corrected_raw_value: str,
        corrected_normalized_value: str | None,
        corrected_value_type: str,
        reason: str,
        request_id: str | None,
    ) -> tuple[ExtractedField, list[ExtractionFieldCorrection]]:
        self._require_client_access(principal=principal, client_id=client_id)
        field = self._extractions.get_field_for_run(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            run_id=run_id,
            field_id=field_id,
        )
        if field is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")
        if not reason.strip():
            raise ApiError(status_code=422, code="invalid_request", message="Reason is required.")
        try:
            validated = validate_provider_field(
                ProviderExtractedField(
                    field_path="correction.value",
                    value_type=corrected_value_type,
                    raw_value=corrected_raw_value,
                    normalized_value=corrected_normalized_value,
                ),
                max_value_chars=self._settings.extraction_max_value_chars,
            )
        except ProviderOutputValidationError as exc:
            raise ApiError(
                status_code=422,
                code="invalid_correction",
                message="Correction value is invalid.",
            ) from exc

        locked_field = self._extractions.lock_field_for_correction(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            run_id=run_id,
            field_id=field.id,
        )
        if locked_field is None:
            raise ApiError(status_code=404, code="not_found", message="Not found.")

        revision_number = self._extractions.next_revision_number(field_id=locked_field.id)
        correction = ExtractionFieldCorrection(
            field_id=locked_field.id,
            extraction_run_id=locked_field.extraction_run_id,
            firm_id=locked_field.firm_id,
            client_id=locked_field.client_id,
            document_id=locked_field.document_id,
            corrected_by_user_id=principal.user_id,
            corrected_by_membership_id=principal.membership_id,
            revision_number=revision_number,
            corrected_raw_value=validated.raw_value,
            corrected_normalized_value=validated.normalized_value,
            corrected_value_type=validated.value_type.value,
            reason=reason.strip(),
        )
        self._extractions.add_correction(correction)
        self._audit.record_event(
            firm_id=principal.firm_id,
            client_id=client_id,
            actor_user_id=principal.user_id,
            event_type=AuditEventType.EXTRACTION_CORRECTION_RECORDED.value,
            target_type="extracted_field",
            target_id=str(field.id),
            request_id=request_id,
            metadata={
                "run_id": str(run_id),
                "field_id": str(field.id),
                "revision_number": revision_number,
            },
        )
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise
        corrections = self._extractions.list_corrections_for_field(
            firm_id=principal.firm_id,
            client_id=client_id,
            document_id=document_id,
            run_id=run_id,
            field_id=field_id,
        )
        return locked_field, corrections

    def _run_provider(
        self,
        *,
        document_file: DocumentFile,
        run: ExtractionRun,
        media_type: str,
    ) -> ExtractionProviderResult:
        with self._storage.open_for_processing(document_file.storage_key) as source_file:
            return self._provider.extract(
                source_file=source_file,
                context=ExtractionRequestContext(
                    firm_id=run.firm_id,
                    client_id=run.client_id,
                    document_id=run.document_id,
                    document_file_id=run.document_file_id,
                    source_sha256=run.source_sha256,
                    media_type=media_type,
                ),
            )

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
        document_file: DocumentFile,
        request_id: str | None,
    ) -> ExtractionRun:
        metadata = self._provider.metadata
        return ExtractionRun(
            id=uuid.uuid4(),
            firm_id=principal.firm_id,
            client_id=document_file.client_id,
            document_id=document_file.document_id,
            document_file_id=document_file.id,
            initiated_by_user_id=principal.user_id,
            initiated_by_membership_id=principal.membership_id,
            status=ExtractionRunStatus.PENDING.value,
            provider_name=metadata.provider_name,
            provider_version=metadata.provider_version,
            model_version=metadata.model_version,
            extraction_schema_version=metadata.extraction_schema_version,
            source_sha256=document_file.sha256,
            request_id=request_id,
        )

    def _transition(self, run: ExtractionRun, status: ExtractionRunStatus) -> None:
        current_status = ExtractionRunStatus(run.status)
        run.status = transition_extraction_status(current_status, status).value
        if status == ExtractionRunStatus.RUNNING:
            run.started_at = datetime.now(UTC)
        if status in {ExtractionRunStatus.SUCCEEDED, ExtractionRunStatus.FAILED}:
            run.completed_at = datetime.now(UTC)

    def _fail_run(
        self,
        *,
        run: ExtractionRun,
        principal: Principal,
        client_id: UUID,
        request_id: str | None,
        failure_code: ExtractionFailureCode,
    ) -> None:
        self._transition(run, ExtractionRunStatus.FAILED)
        run.failure_code = failure_code.value
        self._record_extraction_event(
            event_type=AuditEventType.EXTRACTION_FAILED,
            principal=principal,
            client_id=client_id,
            run=run,
            request_id=request_id,
            metadata={**_run_event_metadata(run), "failure_code": failure_code.value},
        )

    def _fail_run_and_commit(
        self,
        *,
        run: ExtractionRun,
        principal: Principal,
        client_id: UUID,
        request_id: str | None,
        failure_code: ExtractionFailureCode,
    ) -> None:
        self._fail_run(
            run=run,
            principal=principal,
            client_id=client_id,
            request_id=request_id,
            failure_code=failure_code,
        )
        try:
            self._session.commit()
        except SQLAlchemyError as exc:
            self._raise_persistence_error(run=run, request_id=request_id, exc=exc)

    def _raise_persistence_error(
        self,
        *,
        run: ExtractionRun,
        request_id: str | None,
        exc: SQLAlchemyError,
    ) -> None:
        self._session.rollback()
        logger.warning(
            "Extraction persistence failed",
            extra={
                "request_id": request_id,
                "run_id": str(run.id),
                "failure_code": ExtractionFailureCode.PERSISTENCE_FAILED.value,
                "exception_type": type(exc).__name__,
            },
        )
        raise ApiError(
            status_code=503,
            code=ExtractionFailureCode.PERSISTENCE_FAILED.value,
            message="Extraction state could not be persisted.",
        ) from exc

    def _record_extraction_event(
        self,
        *,
        event_type: AuditEventType,
        principal: Principal,
        client_id: UUID,
        run: ExtractionRun,
        request_id: str | None,
        metadata: Mapping[str, object | None],
    ) -> None:
        self._audit.record_event(
            firm_id=principal.firm_id,
            client_id=client_id,
            actor_user_id=principal.user_id,
            event_type=event_type.value,
            target_type="extraction_run",
            target_id=str(run.id),
            request_id=request_id,
            metadata=metadata,
        )


def _run_metadata(run: ExtractionRun) -> ExtractionProviderMetadata:
    return ExtractionProviderMetadata(
        provider_name=run.provider_name,
        provider_version=run.provider_version,
        model_version=run.model_version,
        extraction_schema_version=run.extraction_schema_version,
    )


def _run_event_metadata(run: ExtractionRun) -> dict[str, object | None]:
    return {
        "run_id": str(run.id),
        "document_id": str(run.document_id),
        "document_file_id": str(run.document_file_id),
        "provider_name": run.provider_name,
        "provider_version": run.provider_version,
        "model_version": run.model_version,
        "extraction_schema_version": run.extraction_schema_version,
    }
