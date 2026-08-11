from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ledgerpilot.extraction.states import ExtractionRunStatus
from ledgerpilot.extraction.types import ExtractionFailureCode, ExtractionValueType
from ledgerpilot.persistence.base import Base, utc_now

_EXTRACTION_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in ExtractionRunStatus)
_EXTRACTION_FAILURE_VALUES = ", ".join(f"'{code.value}'" for code in ExtractionFailureCode)
_EXTRACTION_VALUE_TYPE_VALUES = ", ".join(
    f"'{value_type.value}'" for value_type in ExtractionValueType
)


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (
        CheckConstraint(
            f"status in ({_EXTRACTION_STATUS_VALUES})",
            name="ck_extraction_runs_status",
        ),
        CheckConstraint(
            f"failure_code is null or failure_code in ({_EXTRACTION_FAILURE_VALUES})",
            name="ck_extraction_runs_failure_code",
        ),
        CheckConstraint("length(provider_name) > 0", name="ck_extraction_runs_provider_name"),
        CheckConstraint("length(provider_version) > 0", name="ck_extraction_runs_provider_version"),
        CheckConstraint(
            "length(extraction_schema_version) > 0",
            name="ck_extraction_runs_schema_version",
        ),
        CheckConstraint("length(source_sha256) = 64", name="ck_extraction_runs_source_sha256"),
        ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_extraction_runs_client_firm",
        ),
        ForeignKeyConstraint(
            ["document_id", "firm_id", "client_id"],
            ["documents.id", "documents.firm_id", "documents.client_id"],
            name="fk_extraction_runs_document_scope",
        ),
        ForeignKeyConstraint(
            ["document_file_id", "document_id", "firm_id", "client_id"],
            [
                "document_files.id",
                "document_files.document_id",
                "document_files.firm_id",
                "document_files.client_id",
            ],
            name="fk_extraction_runs_document_file_scope",
        ),
        ForeignKeyConstraint(
            ["initiated_by_membership_id", "initiated_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_extraction_runs_initiator_membership_user_firm",
        ),
        UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "document_id",
            name="uq_extraction_runs_id_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("firms.id"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    initiated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    initiated_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    extraction_schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    __table_args__ = (
        CheckConstraint("length(field_path) > 0", name="ck_extracted_fields_field_path"),
        CheckConstraint(
            f"value_type in ({_EXTRACTION_VALUE_TYPE_VALUES})",
            name="ck_extracted_fields_value_type",
        ),
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_extracted_fields_confidence_range",
        ),
        CheckConstraint(
            "source_page_number is null or source_page_number >= 1",
            name="ck_extracted_fields_source_page_number",
        ),
        CheckConstraint("length(raw_value) <= 4000", name="ck_extracted_fields_raw_value_length"),
        CheckConstraint(
            "normalized_value is null or length(normalized_value) <= 4000",
            name="ck_extracted_fields_normalized_value_length",
        ),
        ForeignKeyConstraint(
            ["extraction_run_id", "firm_id", "client_id", "document_id"],
            [
                "extraction_runs.id",
                "extraction_runs.firm_id",
                "extraction_runs.client_id",
                "extraction_runs.document_id",
            ],
            name="fk_extracted_fields_run_scope",
        ),
        UniqueConstraint(
            "extraction_run_id",
            "field_path",
            name="uq_extracted_fields_run_field_path",
        ),
        UniqueConstraint(
            "id",
            "extraction_run_id",
            "firm_id",
            "client_id",
            "document_id",
            name="uq_extracted_fields_id_run_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    field_path: Mapped[str] = mapped_column(String(255), nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_value: Mapped[str] = mapped_column(String(4000), nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    source_page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_locator: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class ExtractionFieldCorrection(Base):
    __tablename__ = "extraction_field_corrections"
    __table_args__ = (
        CheckConstraint("revision_number >= 1", name="ck_extraction_corrections_revision"),
        CheckConstraint(
            f"corrected_value_type in ({_EXTRACTION_VALUE_TYPE_VALUES})",
            name="ck_extraction_corrections_value_type",
        ),
        CheckConstraint("length(reason) > 0", name="ck_extraction_corrections_reason"),
        CheckConstraint(
            "length(corrected_raw_value) <= 4000",
            name="ck_extraction_corrections_raw_value_length",
        ),
        CheckConstraint(
            "corrected_normalized_value is null or length(corrected_normalized_value) <= 4000",
            name="ck_extraction_corrections_normalized_value_length",
        ),
        ForeignKeyConstraint(
            ["field_id", "extraction_run_id", "firm_id", "client_id", "document_id"],
            [
                "extracted_fields.id",
                "extracted_fields.extraction_run_id",
                "extracted_fields.firm_id",
                "extracted_fields.client_id",
                "extracted_fields.document_id",
            ],
            name="fk_extraction_corrections_field_scope",
        ),
        ForeignKeyConstraint(
            ["corrected_by_membership_id", "corrected_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_extraction_corrections_corrector_membership_user_firm",
        ),
        UniqueConstraint(
            "field_id",
            "revision_number",
            name="uq_extraction_corrections_field_revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    corrected_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    corrected_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    corrected_raw_value: Mapped[str] = mapped_column(String(4000), nullable=False)
    corrected_normalized_value: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    corrected_value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
