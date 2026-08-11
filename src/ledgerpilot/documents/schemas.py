from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ledgerpilot.persistence.models.documents import Document


class DocumentMetadataResponse(BaseModel):
    id: UUID
    client_id: UUID
    status: str
    submitted_filename: str
    media_type: str | None
    size_bytes: int | None
    sha256: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_document(cls, document: Document) -> DocumentMetadataResponse:
        return cls(
            id=document.id,
            client_id=document.client_id,
            status=document.status,
            submitted_filename=document.submitted_filename,
            media_type=document.detected_media_type,
            size_bytes=document.size_bytes,
            sha256=document.sha256,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
