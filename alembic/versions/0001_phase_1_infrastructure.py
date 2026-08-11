"""phase 1 infrastructure tables

Revision ID: 0001_phase_1
Revises:
Create Date: 2026-08-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_phase_1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "firms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('active', 'suspended', 'archived')",
            name="ck_firms_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_subject", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_subject", name="uq_users_external_subject"),
    )

    op.create_table(
        "firm_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role in ("
            "'firm_admin', 'accountant', 'senior_reviewer', 'client_submitter', 'auditor'"
            ")",
            name="ck_firm_memberships_role",
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "firm_id", name="uq_firm_memberships_id_firm_id"),
        sa.UniqueConstraint("user_id", "firm_id", name="uq_firm_memberships_user_firm"),
    )
    op.create_index("ix_firm_memberships_firm_id", "firm_memberships", ["firm_id"])
    op.create_index("ix_firm_memberships_user_id", "firm_memberships", ["user_id"])

    op.create_table(
        "client_entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('active', 'inactive', 'archived')",
            name="ck_client_entities_status",
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "firm_id", name="uq_client_entities_id_firm_id"),
        sa.UniqueConstraint("firm_id", "name", name="uq_client_entities_firm_name"),
    )
    op.create_index("ix_client_entities_firm_id", "client_entities", ["firm_id"])

    op.create_table(
        "client_access",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["membership_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.firm_id"],
            name="fk_client_access_membership_firm",
        ),
        sa.ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_client_access_client_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "membership_id",
            "client_id",
            name="uq_client_access_membership_client",
        ),
    )
    op.create_index("ix_client_access_firm_id", "client_access", ["firm_id"])
    op.create_index("ix_client_access_client_id", "client_access", ["client_id"])
    op.create_index("ix_client_access_membership_id", "client_access", ["membership_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=120), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["client_entities.id"]),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_firm_occurred", "audit_events", ["firm_id", "occurred_at"])
    op.create_index("ix_audit_events_client_id", "audit_events", ["client_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_request_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_client_id", table_name="audit_events")
    op.drop_index("ix_audit_events_firm_occurred", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_client_access_membership_id", table_name="client_access")
    op.drop_index("ix_client_access_client_id", table_name="client_access")
    op.drop_index("ix_client_access_firm_id", table_name="client_access")
    op.drop_table("client_access")

    op.drop_index("ix_client_entities_firm_id", table_name="client_entities")
    op.drop_table("client_entities")

    op.drop_index("ix_firm_memberships_user_id", table_name="firm_memberships")
    op.drop_index("ix_firm_memberships_firm_id", table_name="firm_memberships")
    op.drop_table("firm_memberships")

    op.drop_table("users")
    op.drop_table("firms")
