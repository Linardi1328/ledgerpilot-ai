from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ledgerpilot.documents.states import DocumentStatus
from ledgerpilot.documents.types import DocumentFileArea, DocumentMediaType
from ledgerpilot.persistence.base import Base, utc_now

_DOCUMENT_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in DocumentStatus)
_DOCUMENT_FILE_AREA_VALUES = ", ".join(f"'{area.value}'" for area in DocumentFileArea)
_DOCUMENT_MEDIA_TYPE_VALUES = ", ".join(f"'{media_type.value}'" for media_type in DocumentMediaType)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(f"status in ({_DOCUMENT_STATUS_VALUES})", name="ck_documents_status"),
        CheckConstraint(
            "declared_media_type is null "
            f"or declared_media_type in ({_DOCUMENT_MEDIA_TYPE_VALUES})",
            name="ck_documents_declared_media_type",
        ),
        CheckConstraint(
            "detected_media_type is null "
            f"or detected_media_type in ({_DOCUMENT_MEDIA_TYPE_VALUES})",
            name="ck_documents_detected_media_type",
        ),
        CheckConstraint("size_bytes is null or size_bytes >= 0", name="ck_documents_size_bytes"),
        UniqueConstraint("id", "firm_id", "client_id", name="uq_documents_id_firm_client"),
        ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_documents_client_firm",
        ),
        ForeignKeyConstraint(
            ["submitted_by_membership_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.firm_id"],
            name="fk_documents_submitter_membership_firm",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("firms.id"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    submitted_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    submitted_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    declared_media_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    detected_media_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class DocumentFile(Base):
    __tablename__ = "document_files"
    __table_args__ = (
        CheckConstraint(
            f"storage_area in ({_DOCUMENT_FILE_AREA_VALUES})",
            name="ck_document_files_storage_area",
        ),
        CheckConstraint("size_bytes >= 0", name="ck_document_files_size_bytes"),
        ForeignKeyConstraint(
            ["document_id", "firm_id", "client_id"],
            ["documents.id", "documents.firm_id", "documents.client_id"],
            name="fk_document_files_document_scope",
        ),
        UniqueConstraint(
            "document_id",
            "storage_area",
            name="uq_document_files_document_storage_area",
        ),
        UniqueConstraint(
            "storage_backend",
            "storage_key",
            name="uq_document_files_storage_backend_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    storage_backend: Mapped[str] = mapped_column(String(40), nullable=False)
    storage_area: Mapped[str] = mapped_column(String(40), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
