from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from ledgerpilot.api.dependencies import (
    get_document_storage,
    get_malware_scanner,
    get_session,
    get_settings,
    require_permission,
)
from ledgerpilot.api.errors import get_request_id
from ledgerpilot.core.config import Settings
from ledgerpilot.documents.schemas import DocumentMetadataResponse
from ledgerpilot.documents.service import DocumentIntakeService
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.scanning.protocol import MalwareScanner
from ledgerpilot.storage.protocol import DocumentStorage

router = APIRouter(prefix="/clients/{client_id}/documents")


@router.post(
    "",
    response_model=DocumentMetadataResponse,
    status_code=201,
)
async def upload_document(
    request: Request,
    client_id: UUID,
    file: Annotated[UploadFile, File()],
    principal: Annotated[Principal, Depends(require_permission(Permission.UPLOAD_DOCUMENTS))],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    scanner: Annotated[MalwareScanner, Depends(get_malware_scanner)],
) -> DocumentMetadataResponse:
    document = await DocumentIntakeService(
        session=session,
        settings=settings,
        storage=storage,
        scanner=scanner,
    ).submit_document(
        principal=principal,
        client_id=client_id,
        upload_file=file,
        request_id=get_request_id(request),
    )
    return DocumentMetadataResponse.from_document(document)


@router.get(
    "/{document_id}",
    response_model=DocumentMetadataResponse,
)
def get_document_metadata(
    client_id: UUID,
    document_id: UUID,
    principal: Annotated[Principal, Depends(require_permission(Permission.VIEW_DOCUMENTS))],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
    scanner: Annotated[MalwareScanner, Depends(get_malware_scanner)],
) -> DocumentMetadataResponse:
    document = DocumentIntakeService(
        session=session,
        settings=settings,
        storage=storage,
        scanner=scanner,
    ).get_document_metadata(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
    )
    return DocumentMetadataResponse.from_document(document)
