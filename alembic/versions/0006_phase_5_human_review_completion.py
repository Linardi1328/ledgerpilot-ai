"""phase 5 human review completion

Revision ID: 0006_phase_5_review
Revises: 0005_phase_5
Create Date: 2026-08-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_phase_5_review"
down_revision: str | None = "0005_phase_5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("review_tasks") as batch_op:
        batch_op.drop_constraint("ck_review_tasks_state_consistency", type_="check")
        batch_op.drop_constraint("ck_review_tasks_status", type_="check")
        batch_op.add_column(
            sa.Column(
                "risk_class",
                sa.String(length=32),
                nullable=False,
                server_default="blocked",
            )
        )
        batch_op.create_check_constraint(
            "ck_review_tasks_status",
            "status in ('open', 'escalated', 'information_requested', 'approved', 'rejected')",
        )
        batch_op.create_check_constraint(
            "ck_review_tasks_risk_class",
            "risk_class in ('ordinary', 'senior_review_required', 'blocked')",
        )
        batch_op.create_check_constraint(
            "ck_review_tasks_state_consistency",
            "("
            "(escalation_state = 'none' and escalated_at is null) "
            "or (escalation_state = 'senior_review' and escalated_at is not null)"
            ") and ("
            "(status = 'open' and escalation_state = 'none') "
            "or (status = 'escalated' and escalation_state = 'senior_review') "
            "or status in ('information_requested', 'approved', 'rejected')"
            ")",
        )
        batch_op.create_index("ix_review_tasks_risk_class", ["risk_class"])

    op.create_table(
        "review_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_task_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("author_membership_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("body", sa.String(length=2000), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind in ('comment', 'escalation_reason', 'information_request', "
            "'information_response')",
            name="ck_review_comments_kind",
        ),
        sa.CheckConstraint(
            "length(body) > 0",
            name="ck_review_comments_body_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["review_task_id", "firm_id", "client_id", "decision_run_id"],
            [
                "review_tasks.id",
                "review_tasks.firm_id",
                "review_tasks.client_id",
                "review_tasks.decision_run_id",
            ],
            name="fk_review_comments_task_scope",
        ),
        sa.ForeignKeyConstraint(
            ["author_membership_id", "author_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_review_comments_author_membership_user_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "review_task_id",
        "firm_id",
        "client_id",
        "decision_run_id",
        "kind",
        "request_id",
    ):
        op.create_index(f"ix_review_comments_{column}", "review_comments", [column])

    op.create_table(
        "review_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_task_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=False),
        sa.Column("outcome_type", sa.String(length=40), nullable=False),
        sa.Column("proposed_journal_id", sa.Uuid(), nullable=True),
        sa.Column("source_correction_count", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome_type in ('approved', 'corrected_and_approved', 'rejected')",
            name="ck_review_outcomes_type",
        ),
        sa.CheckConstraint(
            "source_correction_count >= 0",
            name="ck_review_outcomes_correction_count_nonnegative",
        ),
        sa.CheckConstraint(
            "("
            "(outcome_type = 'rejected' and reason is not null and length(reason) > 0 "
            "and proposed_journal_id is null) "
            "or (outcome_type in ('approved', 'corrected_and_approved') "
            "and proposed_journal_id is not null)"
            ")",
            name="ck_review_outcomes_resolution_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["review_task_id", "firm_id", "client_id", "decision_run_id"],
            [
                "review_tasks.id",
                "review_tasks.firm_id",
                "review_tasks.client_id",
                "review_tasks.decision_run_id",
            ],
            name="fk_review_outcomes_task_scope",
        ),
        sa.ForeignKeyConstraint(
            ["actor_membership_id", "actor_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_review_outcomes_actor_membership_user_firm",
        ),
        sa.ForeignKeyConstraint(
            [
                "proposed_journal_id",
                "decision_run_id",
                "firm_id",
                "client_id",
                "document_id",
                "extraction_run_id",
            ],
            [
                "proposed_journals.id",
                "proposed_journals.decision_run_id",
                "proposed_journals.firm_id",
                "proposed_journals.client_id",
                "proposed_journals.document_id",
                "proposed_journals.extraction_run_id",
            ],
            name="fk_review_outcomes_journal_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_task_id", name="uq_review_outcomes_review_task"),
    )
    for column in (
        "review_task_id",
        "firm_id",
        "client_id",
        "decision_run_id",
        "outcome_type",
        "request_id",
    ):
        op.create_index(f"ix_review_outcomes_{column}", "review_outcomes", [column])


def downgrade() -> None:
    for column in reversed(
        (
            "review_task_id",
            "firm_id",
            "client_id",
            "decision_run_id",
            "outcome_type",
            "request_id",
        )
    ):
        op.drop_index(f"ix_review_outcomes_{column}", table_name="review_outcomes")
    op.drop_table("review_outcomes")

    for column in reversed(
        (
            "review_task_id",
            "firm_id",
            "client_id",
            "decision_run_id",
            "kind",
            "request_id",
        )
    ):
        op.drop_index(f"ix_review_comments_{column}", table_name="review_comments")
    op.drop_table("review_comments")

    with op.batch_alter_table("review_tasks") as batch_op:
        batch_op.drop_index("ix_review_tasks_risk_class")
        batch_op.drop_constraint("ck_review_tasks_state_consistency", type_="check")
        batch_op.drop_constraint("ck_review_tasks_risk_class", type_="check")
        batch_op.drop_constraint("ck_review_tasks_status", type_="check")
        batch_op.create_check_constraint(
            "ck_review_tasks_status",
            "status in ('open', 'escalated')",
        )
        batch_op.create_check_constraint(
            "ck_review_tasks_state_consistency",
            "(status = 'open' and escalation_state = 'none' and escalated_at is null) "
            "or (status = 'escalated' and escalation_state = 'senior_review' "
            "and escalated_at is not null)",
        )
        batch_op.drop_column("risk_class")
