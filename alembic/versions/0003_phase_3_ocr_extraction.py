"""phase 3 ocr and structured extraction

Revision ID: 0003_phase_3
Revises: 0002_phase_2
Create Date: 2026-08-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_phase_3"
down_revision: str | None = "0002_phase_2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("document_files") as batch_op:
        batch_op.create_unique_constraint(
            "uq_document_files_id_document_scope",
            ["id", "document_id", "firm_id", "client_id"],
        )

    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_file_id", sa.Uuid(), nullable=False),
        sa.Column("initiated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("initiated_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("provider_version", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=True),
        sa.Column("extraction_schema_version", sa.String(length=80), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'succeeded', 'failed')",
            name="ck_extraction_runs_status",
        ),
        sa.CheckConstraint(
            "failure_code is null or failure_code in ("
            "'source_not_eligible', 'source_file_missing', 'provider_disabled', "
            "'provider_failed', 'invalid_provider_output'"
            ")",
            name="ck_extraction_runs_failure_code",
        ),
        sa.CheckConstraint("length(provider_name) > 0", name="ck_extraction_runs_provider_name"),
        sa.CheckConstraint(
            "length(provider_version) > 0",
            name="ck_extraction_runs_provider_version",
        ),
        sa.CheckConstraint(
            "length(extraction_schema_version) > 0",
            name="ck_extraction_runs_schema_version",
        ),
        sa.CheckConstraint("length(source_sha256) = 64", name="ck_extraction_runs_source_sha256"),
        sa.ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_extraction_runs_client_firm",
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.ForeignKeyConstraint(
            ["document_id", "firm_id", "client_id"],
            ["documents.id", "documents.firm_id", "documents.client_id"],
            name="fk_extraction_runs_document_scope",
        ),
        sa.ForeignKeyConstraint(
            ["document_file_id", "document_id", "firm_id", "client_id"],
            [
                "document_files.id",
                "document_files.document_id",
                "document_files.firm_id",
                "document_files.client_id",
            ],
            name="fk_extraction_runs_document_file_scope",
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by_membership_id", "initiated_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_extraction_runs_initiator_membership_user_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "document_id",
            name="uq_extraction_runs_id_scope",
        ),
    )
    op.create_index("ix_extraction_runs_client_id", "extraction_runs", ["client_id"])
    op.create_index("ix_extraction_runs_document_file_id", "extraction_runs", ["document_file_id"])
    op.create_index("ix_extraction_runs_document_id", "extraction_runs", ["document_id"])
    op.create_index("ix_extraction_runs_firm_id", "extraction_runs", ["firm_id"])
    op.create_index(
        "ix_extraction_runs_initiated_by_membership_id",
        "extraction_runs",
        ["initiated_by_membership_id"],
    )
    op.create_index(
        "ix_extraction_runs_initiated_by_user_id",
        "extraction_runs",
        ["initiated_by_user_id"],
    )
    op.create_index("ix_extraction_runs_request_id", "extraction_runs", ["request_id"])
    op.create_index("ix_extraction_runs_status", "extraction_runs", ["status"])

    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("field_path", sa.String(length=255), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("raw_value", sa.String(length=4000), nullable=False),
        sa.Column("normalized_value", sa.String(length=4000), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("source_page_number", sa.Integer(), nullable=True),
        sa.Column("source_locator", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(field_path) > 0", name="ck_extracted_fields_field_path"),
        sa.CheckConstraint(
            "value_type in ('text', 'decimal', 'date', 'integer', 'boolean')",
            name="ck_extracted_fields_value_type",
        ),
        sa.CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_extracted_fields_confidence_range",
        ),
        sa.CheckConstraint(
            "source_page_number is null or source_page_number >= 1",
            name="ck_extracted_fields_source_page_number",
        ),
        sa.CheckConstraint(
            "length(raw_value) <= 4000",
            name="ck_extracted_fields_raw_value_length",
        ),
        sa.CheckConstraint(
            "normalized_value is null or length(normalized_value) <= 4000",
            name="ck_extracted_fields_normalized_value_length",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id", "firm_id", "client_id", "document_id"],
            [
                "extraction_runs.id",
                "extraction_runs.firm_id",
                "extraction_runs.client_id",
                "extraction_runs.document_id",
            ],
            name="fk_extracted_fields_run_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "extraction_run_id",
            "field_path",
            name="uq_extracted_fields_run_field_path",
        ),
        sa.UniqueConstraint(
            "id",
            "extraction_run_id",
            "firm_id",
            "client_id",
            "document_id",
            name="uq_extracted_fields_id_run_scope",
        ),
    )
    op.create_index("ix_extracted_fields_client_id", "extracted_fields", ["client_id"])
    op.create_index("ix_extracted_fields_document_id", "extracted_fields", ["document_id"])
    op.create_index(
        "ix_extracted_fields_extraction_run_id",
        "extracted_fields",
        ["extraction_run_id"],
    )
    op.create_index("ix_extracted_fields_firm_id", "extracted_fields", ["firm_id"])

    op.create_table(
        "extraction_field_corrections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("corrected_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("corrected_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("corrected_raw_value", sa.String(length=4000), nullable=False),
        sa.Column("corrected_normalized_value", sa.String(length=4000), nullable=True),
        sa.Column("corrected_value_type", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision_number >= 1", name="ck_extraction_corrections_revision"),
        sa.CheckConstraint(
            "corrected_value_type in ('text', 'decimal', 'date', 'integer', 'boolean')",
            name="ck_extraction_corrections_value_type",
        ),
        sa.CheckConstraint("length(reason) > 0", name="ck_extraction_corrections_reason"),
        sa.CheckConstraint(
            "length(corrected_raw_value) <= 4000",
            name="ck_extraction_corrections_raw_value_length",
        ),
        sa.CheckConstraint(
            "corrected_normalized_value is null or length(corrected_normalized_value) <= 4000",
            name="ck_extraction_corrections_normalized_value_length",
        ),
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
            ["corrected_by_membership_id", "corrected_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_extraction_corrections_corrector_membership_user_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "field_id",
            "revision_number",
            name="uq_extraction_corrections_field_revision",
        ),
    )
    op.create_index(
        "ix_extraction_field_corrections_client_id",
        "extraction_field_corrections",
        ["client_id"],
    )
    op.create_index(
        "ix_extraction_field_corrections_corrected_by_membership_id",
        "extraction_field_corrections",
        ["corrected_by_membership_id"],
    )
    op.create_index(
        "ix_extraction_field_corrections_corrected_by_user_id",
        "extraction_field_corrections",
        ["corrected_by_user_id"],
    )
    op.create_index(
        "ix_extraction_field_corrections_document_id",
        "extraction_field_corrections",
        ["document_id"],
    )
    op.create_index(
        "ix_extraction_field_corrections_extraction_run_id",
        "extraction_field_corrections",
        ["extraction_run_id"],
    )
    op.create_index(
        "ix_extraction_field_corrections_field_id",
        "extraction_field_corrections",
        ["field_id"],
    )
    op.create_index(
        "ix_extraction_field_corrections_firm_id",
        "extraction_field_corrections",
        ["firm_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_extraction_field_corrections_firm_id",
        table_name="extraction_field_corrections",
    )
    op.drop_index(
        "ix_extraction_field_corrections_field_id",
        table_name="extraction_field_corrections",
    )
    op.drop_index(
        "ix_extraction_field_corrections_extraction_run_id",
        table_name="extraction_field_corrections",
    )
    op.drop_index(
        "ix_extraction_field_corrections_document_id",
        table_name="extraction_field_corrections",
    )
    op.drop_index(
        "ix_extraction_field_corrections_corrected_by_user_id",
        table_name="extraction_field_corrections",
    )
    op.drop_index(
        "ix_extraction_field_corrections_corrected_by_membership_id",
        table_name="extraction_field_corrections",
    )
    op.drop_index(
        "ix_extraction_field_corrections_client_id",
        table_name="extraction_field_corrections",
    )
    op.drop_table("extraction_field_corrections")

    op.drop_index("ix_extracted_fields_firm_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_extraction_run_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_document_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_client_id", table_name="extracted_fields")
    op.drop_table("extracted_fields")

    op.drop_index("ix_extraction_runs_status", table_name="extraction_runs")
    op.drop_index("ix_extraction_runs_request_id", table_name="extraction_runs")
    op.drop_index("ix_extraction_runs_initiated_by_user_id", table_name="extraction_runs")
    op.drop_index("ix_extraction_runs_initiated_by_membership_id", table_name="extraction_runs")
    op.drop_index("ix_extraction_runs_firm_id", table_name="extraction_runs")
    op.drop_index("ix_extraction_runs_document_id", table_name="extraction_runs")
    op.drop_index("ix_extraction_runs_document_file_id", table_name="extraction_runs")
    op.drop_index("ix_extraction_runs_client_id", table_name="extraction_runs")
    op.drop_table("extraction_runs")

    with op.batch_alter_table("document_files") as batch_op:
        batch_op.drop_constraint(
            "uq_document_files_id_document_scope",
            type_="unique",
        )
