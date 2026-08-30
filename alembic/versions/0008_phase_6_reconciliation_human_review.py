"""phase 6 human reconciliation review and outcomes

Revision ID: 0008_phase_6_recon_review
Revises: 0007_phase_6_reconciliation
Create Date: 2026-08-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_phase_6_recon_review"
down_revision: str | None = "0007_phase_6_reconciliation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bank_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("match_run_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("selected_review_outcome_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('open', 'disputed', 'matched', 'unmatched')",
            name="ck_reconciliation_reviews_status",
        ),
        sa.ForeignKeyConstraint(
            ["bank_transaction_id", "firm_id", "client_id"],
            [
                "bank_transactions.id",
                "bank_transactions.firm_id",
                "bank_transactions.client_id",
            ],
            name="fk_reconciliation_reviews_transaction_scope",
        ),
        sa.ForeignKeyConstraint(
            ["match_run_id", "firm_id", "client_id", "bank_transaction_id"],
            [
                "reconciliation_match_runs.id",
                "reconciliation_match_runs.firm_id",
                "reconciliation_match_runs.client_id",
                "reconciliation_match_runs.bank_transaction_id",
            ],
            name="fk_reconciliation_reviews_match_run_scope",
        ),
        sa.ForeignKeyConstraint(
            ["match_run_id", "selected_review_outcome_id"],
            [
                "reconciliation_candidates.match_run_id",
                "reconciliation_candidates.review_outcome_id",
            ],
            name="fk_reconciliation_reviews_selected_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id", "created_by_user_id", "firm_id"],
            [
                "firm_memberships.id",
                "firm_memberships.user_id",
                "firm_memberships.firm_id",
            ],
            name="fk_reconciliation_reviews_creator_membership_user_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bank_transaction_id",
            name="uq_reconciliation_reviews_transaction",
        ),
        sa.UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "bank_transaction_id",
            "match_run_id",
            name="uq_reconciliation_reviews_id_scope",
        ),
    )
    for column in (
        "bank_transaction_id",
        "firm_id",
        "client_id",
        "match_run_id",
        "status",
        "selected_review_outcome_id",
    ):
        op.create_index(
            f"ix_reconciliation_reviews_{column}",
            "reconciliation_reviews",
            [column],
        )

    op.create_table(
        "reconciliation_review_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reconciliation_review_id", sa.Uuid(), nullable=False),
        sa.Column("bank_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("match_run_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("candidate_review_outcome_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=2000), nullable=True),
        sa.Column("request_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action_type in "
            "('candidate_selected', 'disputed', 'reopened', 'approved_match', 'marked_unmatched')",
            name="ck_reconciliation_review_actions_type",
        ),
        sa.CheckConstraint(
            "reason is null or length(reason) > 0",
            name="ck_reconciliation_review_actions_reason",
        ),
        sa.ForeignKeyConstraint(
            [
                "reconciliation_review_id",
                "firm_id",
                "client_id",
                "bank_transaction_id",
                "match_run_id",
            ],
            [
                "reconciliation_reviews.id",
                "reconciliation_reviews.firm_id",
                "reconciliation_reviews.client_id",
                "reconciliation_reviews.bank_transaction_id",
                "reconciliation_reviews.match_run_id",
            ],
            name="fk_reconciliation_review_actions_review_scope",
        ),
        sa.ForeignKeyConstraint(
            ["match_run_id", "candidate_review_outcome_id"],
            [
                "reconciliation_candidates.match_run_id",
                "reconciliation_candidates.review_outcome_id",
            ],
            name="fk_reconciliation_review_actions_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["actor_membership_id", "actor_user_id", "firm_id"],
            [
                "firm_memberships.id",
                "firm_memberships.user_id",
                "firm_memberships.firm_id",
            ],
            name="fk_reconciliation_review_actions_actor_membership_user_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "reconciliation_review_id",
        "bank_transaction_id",
        "firm_id",
        "client_id",
        "match_run_id",
        "action_type",
        "candidate_review_outcome_id",
    ):
        op.create_index(
            f"ix_reconciliation_review_actions_{column}",
            "reconciliation_review_actions",
            [column],
        )

    op.create_table(
        "reconciliation_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reconciliation_review_id", sa.Uuid(), nullable=False),
        sa.Column("bank_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("match_run_id", sa.Uuid(), nullable=False),
        sa.Column("matched_review_outcome_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=False),
        sa.Column("outcome_type", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=2000), nullable=True),
        sa.Column("request_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome_type in ('matched', 'unmatched')",
            name="ck_reconciliation_outcomes_type",
        ),
        sa.CheckConstraint(
            "(outcome_type = 'matched' and matched_review_outcome_id is not null) "
            "or (outcome_type = 'unmatched' and matched_review_outcome_id is null "
            "and reason is not null and length(reason) > 0)",
            name="ck_reconciliation_outcomes_resolution_consistency",
        ),
        sa.ForeignKeyConstraint(
            [
                "reconciliation_review_id",
                "firm_id",
                "client_id",
                "bank_transaction_id",
                "match_run_id",
            ],
            [
                "reconciliation_reviews.id",
                "reconciliation_reviews.firm_id",
                "reconciliation_reviews.client_id",
                "reconciliation_reviews.bank_transaction_id",
                "reconciliation_reviews.match_run_id",
            ],
            name="fk_reconciliation_outcomes_review_scope",
        ),
        sa.ForeignKeyConstraint(
            ["match_run_id", "matched_review_outcome_id"],
            [
                "reconciliation_candidates.match_run_id",
                "reconciliation_candidates.review_outcome_id",
            ],
            name="fk_reconciliation_outcomes_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["actor_membership_id", "actor_user_id", "firm_id"],
            [
                "firm_memberships.id",
                "firm_memberships.user_id",
                "firm_memberships.firm_id",
            ],
            name="fk_reconciliation_outcomes_actor_membership_user_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reconciliation_review_id",
            name="uq_reconciliation_outcomes_review",
        ),
        sa.UniqueConstraint(
            "bank_transaction_id",
            name="uq_reconciliation_outcomes_transaction",
        ),
        sa.UniqueConstraint(
            "firm_id",
            "client_id",
            "matched_review_outcome_id",
            name="uq_reconciliation_outcomes_matched_review_outcome",
        ),
    )
    for column in (
        "reconciliation_review_id",
        "bank_transaction_id",
        "firm_id",
        "client_id",
        "match_run_id",
        "matched_review_outcome_id",
        "outcome_type",
    ):
        op.create_index(
            f"ix_reconciliation_outcomes_{column}",
            "reconciliation_outcomes",
            [column],
        )


def downgrade() -> None:
    for column in reversed(
        (
            "reconciliation_review_id",
            "bank_transaction_id",
            "firm_id",
            "client_id",
            "match_run_id",
            "matched_review_outcome_id",
            "outcome_type",
        )
    ):
        op.drop_index(
            f"ix_reconciliation_outcomes_{column}",
            table_name="reconciliation_outcomes",
        )
    op.drop_table("reconciliation_outcomes")

    for column in reversed(
        (
            "reconciliation_review_id",
            "bank_transaction_id",
            "firm_id",
            "client_id",
            "match_run_id",
            "action_type",
            "candidate_review_outcome_id",
        )
    ):
        op.drop_index(
            f"ix_reconciliation_review_actions_{column}",
            table_name="reconciliation_review_actions",
        )
    op.drop_table("reconciliation_review_actions")

    for column in reversed(
        (
            "bank_transaction_id",
            "firm_id",
            "client_id",
            "match_run_id",
            "status",
            "selected_review_outcome_id",
        )
    ):
        op.drop_index(
            f"ix_reconciliation_reviews_{column}",
            table_name="reconciliation_reviews",
        )
    op.drop_table("reconciliation_reviews")
