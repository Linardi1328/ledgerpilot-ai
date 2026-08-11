"""phase 2 secure document intake

Revision ID: 0002_phase_2
Revises: 0001_phase_1
Create Date: 2026-08-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_phase_2"
down_revision: str | None = "0001_phase_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("firm_memberships") as batch_op:
        batch_op.create_unique_constraint(
            "uq_firm_memberships_id_user_firm_id",
            ["id", "user_id", "firm_id"],
        )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("submitted_filename", sa.String(length=255), nullable=False),
        sa.Column("declared_media_type", sa.String(length=80), nullable=True),
        sa.Column("detected_media_type", sa.String(length=80), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ("
            "'uploaded', 'validating', 'validation_failed', 'scan_pending', "
            "'scanning', 'scan_failed', 'quarantined', 'stored', 'rejected'"
            ")",
            name="ck_documents_status",
        ),
        sa.CheckConstraint(
            "declared_media_type is null or declared_media_type in ("
            "'application/pdf', 'image/jpeg', 'image/png'"
            ")",
            name="ck_documents_declared_media_type",
        ),
        sa.CheckConstraint(
            "detected_media_type is null or detected_media_type in ("
            "'application/pdf', 'image/jpeg', 'image/png'"
            ")",
            name="ck_documents_detected_media_type",
        ),
        sa.CheckConstraint(
            "size_bytes is null or size_bytes >= 0",
            name="ck_documents_size_bytes",
        ),
        sa.ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_documents_client_firm",
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.ForeignKeyConstraint(
            ["submitted_by_membership_id", "submitted_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_documents_submitter_membership_user_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "firm_id", "client_id", name="uq_documents_id_firm_client"),
    )
    op.create_index("ix_documents_client_id", "documents", ["client_id"])
    op.create_index(
        "ix_documents_firm_client_status", "documents", ["firm_id", "client_id", "status"]
    )
    op.create_index("ix_documents_firm_id", "documents", ["firm_id"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index(
        "ix_documents_submitted_by_membership_id",
        "documents",
        ["submitted_by_membership_id"],
    )
    op.create_index("ix_documents_submitted_by_user_id", "documents", ["submitted_by_user_id"])

    op.create_table(
        "document_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("storage_backend", sa.String(length=40), nullable=False),
        sa.Column("storage_area", sa.String(length=40), nullable=False),
        sa.Column("storage_key", sa.String(length=400), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "storage_area in ('accepted', 'quarantine')",
            name="ck_document_files_storage_area",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_document_files_size_bytes"),
        sa.ForeignKeyConstraint(
            ["document_id", "firm_id", "client_id"],
            ["documents.id", "documents.firm_id", "documents.client_id"],
            name="fk_document_files_document_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "storage_area",
            name="uq_document_files_document_storage_area",
        ),
        sa.UniqueConstraint(
            "storage_backend",
            "storage_key",
            name="uq_document_files_storage_backend_key",
        ),
    )
    op.create_index("ix_document_files_client_id", "document_files", ["client_id"])
    op.create_index("ix_document_files_document_id", "document_files", ["document_id"])
    op.create_index("ix_document_files_firm_id", "document_files", ["firm_id"])
    op.create_index("ix_document_files_sha256", "document_files", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_document_files_sha256", table_name="document_files")
    op.drop_index("ix_document_files_firm_id", table_name="document_files")
    op.drop_index("ix_document_files_document_id", table_name="document_files")
    op.drop_index("ix_document_files_client_id", table_name="document_files")
    op.drop_table("document_files")

    op.drop_index("ix_documents_submitted_by_user_id", table_name="documents")
    op.drop_index("ix_documents_submitted_by_membership_id", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_index("ix_documents_firm_id", table_name="documents")
    op.drop_index("ix_documents_firm_client_status", table_name="documents")
    op.drop_index("ix_documents_client_id", table_name="documents")
    op.drop_table("documents")
    with op.batch_alter_table("firm_memberships") as batch_op:
        batch_op.drop_constraint(
            "uq_firm_memberships_id_user_firm_id",
            type_="unique",
        )
