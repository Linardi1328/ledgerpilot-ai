from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ledgerpilot.api.dependencies import (
    get_document_storage,
    get_extraction_provider,
    get_session,
    get_settings,
    require_permission,
)
from ledgerpilot.api.errors import get_request_id
from ledgerpilot.core.config import Settings
from ledgerpilot.extraction.protocol import ExtractionProvider
from ledgerpilot.extraction.schemas import (
    ExtractedFieldResponse,
    ExtractionFieldCorrectionRequest,
    ExtractionRunResponse,
    ExtractionRunSummaryResponse,
)
from ledgerpilot.extraction.service import ExtractionService
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.storage.protocol import DocumentStorage

router = APIRouter(prefix="/clients/{client_id}/documents/{document_id}/extractions")


@router.post(
    "",
    response_model=ExtractionRunResponse,
    status_code=201,
)
def start_extraction(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    principal: Annotated[Principal, Depends(require_permission(Permission.RUN_EXTRACTION))],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    provider: Annotated[ExtractionProvider, Depends(get_extraction_provider)],
) -> ExtractionRunResponse:
    service = ExtractionService(
        session=session,
        settings=settings,
        storage=storage,
        provider=provider,
    )
    run = service.start_extraction(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        request_id=get_request_id(request),
    )
    run, fields, corrections = service.get_extraction_run(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        run_id=run.id,
    )
    return ExtractionRunResponse.from_run(run, fields, corrections)


@router.get(
    "",
    response_model=list[ExtractionRunSummaryResponse],
)
def list_extractions(
    client_id: UUID,
    document_id: UUID,
    principal: Annotated[Principal, Depends(require_permission(Permission.VIEW_DOCUMENTS))],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    provider: Annotated[ExtractionProvider, Depends(get_extraction_provider)],
) -> list[ExtractionRunSummaryResponse]:
    runs = ExtractionService(
        session=session,
        settings=settings,
        storage=storage,
        provider=provider,
    ).list_extraction_runs(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
    )
    return [ExtractionRunSummaryResponse.from_run(run) for run in runs]


@router.get(
    "/{run_id}",
    response_model=ExtractionRunResponse,
)
def get_extraction(
    client_id: UUID,
    document_id: UUID,
    run_id: UUID,
    principal: Annotated[Principal, Depends(require_permission(Permission.VIEW_DOCUMENTS))],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    provider: Annotated[ExtractionProvider, Depends(get_extraction_provider)],
) -> ExtractionRunResponse:
    run, fields, corrections = ExtractionService(
        session=session,
        settings=settings,
        storage=storage,
        provider=provider,
    ).get_extraction_run(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        run_id=run_id,
    )
    return ExtractionRunResponse.from_run(run, fields, corrections)


@router.post(
    "/{run_id}/fields/{field_id}/corrections",
    response_model=ExtractedFieldResponse,
    status_code=201,
)
def correct_extracted_field(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    run_id: UUID,
    field_id: UUID,
    correction_request: ExtractionFieldCorrectionRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.CORRECT_EXTRACTED_INFORMATION)),
    ],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    provider: Annotated[ExtractionProvider, Depends(get_extraction_provider)],
) -> ExtractedFieldResponse:
    field, corrections = ExtractionService(
        session=session,
        settings=settings,
        storage=storage,
        provider=provider,
    ).correct_field(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        run_id=run_id,
        field_id=field_id,
        corrected_raw_value=correction_request.corrected_raw_value,
        corrected_normalized_value=correction_request.corrected_normalized_value,
        corrected_value_type=correction_request.corrected_value_type.value,
        reason=correction_request.reason,
        request_id=get_request_id(request),
    )
    return ExtractedFieldResponse.from_field(field, corrections)
