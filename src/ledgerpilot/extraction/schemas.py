from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ledgerpilot.extraction.states import is_extraction_ready_for_downstream
from ledgerpilot.extraction.types import ExtractionValueType
from ledgerpilot.persistence.models.extraction import (
    ExtractedField,
    ExtractionFieldCorrection,
    ExtractionRun,
)


class ExtractionFieldCorrectionRequest(BaseModel):
    corrected_raw_value: str = Field(min_length=1, max_length=4000)
    corrected_normalized_value: str | None = Field(default=None, max_length=4000)
    corrected_value_type: ExtractionValueType
    reason: str = Field(min_length=1, max_length=500)


class ExtractedFieldResponse(BaseModel):
    id: UUID
    field_path: str
    value_type: str
    original_raw_value: str
    original_normalized_value: str | None
    effective_raw_value: str
    effective_normalized_value: str | None
    effective_value_type: str
    confidence: str | None
    source_page_number: int | None
    source_locator: dict[str, Any] | None
    corrected: bool
    latest_correction_id: UUID | None
    latest_revision_number: int | None

    @classmethod
    def from_field(
        cls,
        field: ExtractedField,
        corrections: list[ExtractionFieldCorrection],
    ) -> ExtractedFieldResponse:
        latest = corrections[-1] if corrections else None
        return cls(
            id=field.id,
            field_path=field.field_path,
            value_type=field.value_type,
            original_raw_value=field.raw_value,
            original_normalized_value=field.normalized_value,
            effective_raw_value=latest.corrected_raw_value
            if latest is not None
            else field.raw_value,
            effective_normalized_value=(
                latest.corrected_normalized_value if latest is not None else field.normalized_value
            ),
            effective_value_type=latest.corrected_value_type
            if latest is not None
            else field.value_type,
            confidence=_decimal_to_string(field.confidence),
            source_page_number=field.source_page_number,
            source_locator=field.source_locator,
            corrected=latest is not None,
            latest_correction_id=latest.id if latest is not None else None,
            latest_revision_number=latest.revision_number if latest is not None else None,
        )


class ExtractionRunResponse(BaseModel):
    id: UUID
    client_id: UUID
    document_id: UUID
    document_file_id: UUID
    status: str
    provider_name: str
    provider_version: str
    model_version: str | None
    extraction_schema_version: str
    source_sha256: str
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None
    request_id: str | None
    downstream_ready: bool
    fields: list[ExtractedFieldResponse]

    @classmethod
    def from_run(
        cls,
        run: ExtractionRun,
        fields: list[ExtractedField],
        corrections: list[ExtractionFieldCorrection],
    ) -> ExtractionRunResponse:
        corrections_by_field: dict[UUID, list[ExtractionFieldCorrection]] = {}
        for correction in corrections:
            corrections_by_field.setdefault(correction.field_id, []).append(correction)
        return cls(
            id=run.id,
            client_id=run.client_id,
            document_id=run.document_id,
            document_file_id=run.document_file_id,
            status=run.status,
            provider_name=run.provider_name,
            provider_version=run.provider_version,
            model_version=run.model_version,
            extraction_schema_version=run.extraction_schema_version,
            source_sha256=run.source_sha256,
            started_at=run.started_at,
            completed_at=run.completed_at,
            failure_code=run.failure_code,
            request_id=run.request_id,
            downstream_ready=is_extraction_ready_for_downstream(run.status),
            fields=[
                ExtractedFieldResponse.from_field(field, corrections_by_field.get(field.id, []))
                for field in fields
            ],
        )


class ExtractionRunSummaryResponse(BaseModel):
    id: UUID
    client_id: UUID
    document_id: UUID
    status: str
    provider_name: str
    provider_version: str
    model_version: str | None
    extraction_schema_version: str
    source_sha256: str
    started_at: datetime | None
    completed_at: datetime | None
    failure_code: str | None
    downstream_ready: bool

    @classmethod
    def from_run(cls, run: ExtractionRun) -> ExtractionRunSummaryResponse:
        return cls(
            id=run.id,
            client_id=run.client_id,
            document_id=run.document_id,
            status=run.status,
            provider_name=run.provider_name,
            provider_version=run.provider_version,
            model_version=run.model_version,
            extraction_schema_version=run.extraction_schema_version,
            source_sha256=run.source_sha256,
            started_at=run.started_at,
            completed_at=run.completed_at,
            failure_code=run.failure_code,
            downstream_ready=is_extraction_ready_for_downstream(run.status),
        )


def _decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")
