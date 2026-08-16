"""phase 5 human review first slice

Revision ID: 0005_phase_5
Revises: 0004_phase_4
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_phase_5"
down_revision: str | None = "0004_phase_4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("owner_membership_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("escalation_state", sa.String(length=32), nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('open', 'escalated')",
            name="ck_review_tasks_status",
        ),
        sa.CheckConstraint(
            "escalation_state in ('none', 'senior_review')",
            name="ck_review_tasks_escalation_state",
        ),
        sa.CheckConstraint(
            "(status = 'open' and escalation_state = 'none' and escalated_at is null) "
            "or (status = 'escalated' and escalation_state = 'senior_review' "
            "and escalated_at is not null)",
            name="ck_review_tasks_state_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_review_tasks_client_firm",
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.ForeignKeyConstraint(
            ["decision_run_id", "firm_id", "client_id", "document_id", "extraction_run_id"],
            [
                "accounting_decision_runs.id",
                "accounting_decision_runs.firm_id",
                "accounting_decision_runs.client_id",
                "accounting_decision_runs.document_id",
                "accounting_decision_runs.extraction_run_id",
            ],
            name="fk_review_tasks_decision_scope",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id", "created_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_review_tasks_creator_membership_user_firm",
        ),
        sa.ForeignKeyConstraint(
            ["owner_membership_id", "owner_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_review_tasks_owner_membership_user_firm",
        ),
        sa.ForeignKeyConstraint(
            ["owner_membership_id", "client_id"],
            ["client_access.membership_id", "client_access.client_id"],
            name="fk_review_tasks_owner_client_access",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_run_id", name="uq_review_tasks_decision_run"),
        sa.UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "decision_run_id",
            name="uq_review_tasks_id_scope",
        ),
    )
    for column in (
        "firm_id",
        "client_id",
        "decision_run_id",
        "document_id",
        "extraction_run_id",
        "owner_user_id",
        "owner_membership_id",
        "status",
        "escalation_state",
        "request_id",
    ):
        op.create_index(f"ix_review_tasks_{column}", "review_tasks", [column])


def downgrade() -> None:
    for column in reversed(
        (
            "firm_id",
            "client_id",
            "decision_run_id",
            "document_id",
            "extraction_run_id",
            "owner_user_id",
            "owner_membership_id",
            "status",
            "escalation_state",
            "request_id",
        )
    ):
        op.drop_index(f"ix_review_tasks_{column}", table_name="review_tasks")
    op.drop_table("review_tasks")
