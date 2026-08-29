"""phase 6 bank reconciliation persistence

Revision ID: 0007_phase_6_reconciliation
Revises: 0006_phase_5_review
Create Date: 2026-08-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_phase_6_reconciliation"
down_revision: str | None = "0006_phase_5_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("review_outcomes") as batch_op:
        batch_op.create_unique_constraint(
            "uq_review_outcomes_id_scope",
            ["id", "firm_id", "client_id", "decision_run_id", "document_id"],
        )

    op.create_table(
        "bank_import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("provider_version", sa.String(length=80), nullable=False),
        sa.Column("provider_batch_reference", sa.String(length=160), nullable=False),
        sa.Column("account_reference", sa.String(length=160), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(provider_name) > 0",
            name="ck_bank_import_batches_provider_name",
        ),
        sa.CheckConstraint(
            "length(provider_version) > 0",
            name="ck_bank_import_batches_provider_version",
        ),
        sa.CheckConstraint(
            "length(provider_batch_reference) > 0",
            name="ck_bank_import_batches_provider_batch_reference",
        ),
        sa.CheckConstraint(
            "length(account_reference) > 0",
            name="ck_bank_import_batches_account_reference",
        ),
        sa.CheckConstraint(
            "period_end >= period_start",
            name="ck_bank_import_batches_period",
        ),
        sa.ForeignKeyConstraint(
            ["firm_id"],
            ["firms.id"],
            name="fk_bank_import_batches_firm",
        ),
        sa.ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_bank_import_batches_client_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "firm_id",
            "client_id",
            "provider_name",
            "account_reference",
            "provider_batch_reference",
            name="uq_bank_import_batches_provider_reference",
        ),
        sa.UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "provider_name",
            "account_reference",
            name="uq_bank_import_batches_id_scope",
        ),
    )
    for column in ("firm_id", "client_id", "provider_name", "account_reference"):
        op.create_index(
            f"ix_bank_import_batches_{column}",
            "bank_import_batches",
            [column],
        )

    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("account_reference", sa.String(length=160), nullable=False),
        sa.Column("source_transaction_id", sa.String(length=200), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("counterparty_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "direction in ('debit', 'credit')",
            name="ck_bank_transactions_direction",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_bank_transactions_amount_positive",
        ),
        sa.CheckConstraint(
            "length(currency) = 3",
            name="ck_bank_transactions_currency",
        ),
        sa.CheckConstraint(
            "length(source_transaction_id) > 0",
            name="ck_bank_transactions_source_transaction_id",
        ),
        sa.CheckConstraint(
            "length(description) > 0",
            name="ck_bank_transactions_description",
        ),
        sa.CheckConstraint(
            "length(provider_name) > 0",
            name="ck_bank_transactions_provider_name",
        ),
        sa.CheckConstraint(
            "length(account_reference) > 0",
            name="ck_bank_transactions_account_reference",
        ),
        sa.ForeignKeyConstraint(
            [
                "import_batch_id",
                "firm_id",
                "client_id",
                "provider_name",
                "account_reference",
            ],
            [
                "bank_import_batches.id",
                "bank_import_batches.firm_id",
                "bank_import_batches.client_id",
                "bank_import_batches.provider_name",
                "bank_import_batches.account_reference",
            ],
            name="fk_bank_transactions_batch_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "firm_id",
            "client_id",
            "provider_name",
            "account_reference",
            "source_transaction_id",
            name="uq_bank_transactions_source_identity",
        ),
        sa.UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            name="uq_bank_transactions_id_scope",
        ),
    )
    for column in (
        "import_batch_id",
        "firm_id",
        "client_id",
        "provider_name",
        "account_reference",
        "source_transaction_id",
        "booking_date",
        "direction",
        "currency",
    ):
        op.create_index(f"ix_bank_transactions_{column}", "bank_transactions", [column])

    op.create_table(
        "reconciliation_match_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bank_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("matcher_name", sa.String(length=80), nullable=False),
        sa.Column("matcher_version", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('unmatched', 'candidates_available')",
            name="ck_reconciliation_match_runs_status",
        ),
        sa.CheckConstraint(
            "length(matcher_name) > 0",
            name="ck_reconciliation_match_runs_matcher_name",
        ),
        sa.CheckConstraint(
            "length(matcher_version) > 0",
            name="ck_reconciliation_match_runs_matcher_version",
        ),
        sa.ForeignKeyConstraint(
            ["bank_transaction_id", "firm_id", "client_id"],
            ["bank_transactions.id", "bank_transactions.firm_id", "bank_transactions.client_id"],
            name="fk_reconciliation_match_runs_transaction_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "bank_transaction_id",
            name="uq_reconciliation_match_runs_id_scope",
        ),
    )
    for column in ("bank_transaction_id", "firm_id", "client_id", "status"):
        op.create_index(
            f"ix_reconciliation_match_runs_{column}",
            "reconciliation_match_runs",
            [column],
        )

    op.create_table(
        "reconciliation_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_run_id", sa.Uuid(), nullable=False),
        sa.Column("bank_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("review_outcome_id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("target_transaction_date", sa.Date(), nullable=False),
        sa.Column("target_direction", sa.String(length=16), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("target_currency", sa.String(length=3), nullable=False),
        sa.Column("target_reference", sa.String(length=255), nullable=True),
        sa.Column("target_counterparty_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "score >= 0 and score <= 1",
            name="ck_reconciliation_candidates_score",
        ),
        sa.CheckConstraint(
            "target_direction in ('debit', 'credit')",
            name="ck_reconciliation_candidates_target_direction",
        ),
        sa.CheckConstraint(
            "target_amount > 0",
            name="ck_reconciliation_candidates_target_amount_positive",
        ),
        sa.CheckConstraint(
            "length(target_currency) = 3",
            name="ck_reconciliation_candidates_target_currency",
        ),
        sa.ForeignKeyConstraint(
            ["match_run_id", "firm_id", "client_id", "bank_transaction_id"],
            [
                "reconciliation_match_runs.id",
                "reconciliation_match_runs.firm_id",
                "reconciliation_match_runs.client_id",
                "reconciliation_match_runs.bank_transaction_id",
            ],
            name="fk_reconciliation_candidates_match_run_scope",
        ),
        sa.ForeignKeyConstraint(
            [
                "review_outcome_id",
                "firm_id",
                "client_id",
                "decision_run_id",
                "document_id",
            ],
            [
                "review_outcomes.id",
                "review_outcomes.firm_id",
                "review_outcomes.client_id",
                "review_outcomes.decision_run_id",
                "review_outcomes.document_id",
            ],
            name="fk_reconciliation_candidates_outcome_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_run_id",
            "review_outcome_id",
            name="uq_reconciliation_candidates_run_outcome",
        ),
    )
    for column in (
        "match_run_id",
        "bank_transaction_id",
        "firm_id",
        "client_id",
        "review_outcome_id",
        "decision_run_id",
        "document_id",
    ):
        op.create_index(
            f"ix_reconciliation_candidates_{column}",
            "reconciliation_candidates",
            [column],
        )


def downgrade() -> None:
    for column in reversed(
        (
            "match_run_id",
            "bank_transaction_id",
            "firm_id",
            "client_id",
            "review_outcome_id",
            "decision_run_id",
            "document_id",
        )
    ):
        op.drop_index(
            f"ix_reconciliation_candidates_{column}",
            table_name="reconciliation_candidates",
        )
    op.drop_table("reconciliation_candidates")

    for column in reversed(("bank_transaction_id", "firm_id", "client_id", "status")):
        op.drop_index(
            f"ix_reconciliation_match_runs_{column}",
            table_name="reconciliation_match_runs",
        )
    op.drop_table("reconciliation_match_runs")

    for column in reversed(
        (
            "import_batch_id",
            "firm_id",
            "client_id",
            "provider_name",
            "account_reference",
            "source_transaction_id",
            "booking_date",
            "direction",
            "currency",
        )
    ):
        op.drop_index(f"ix_bank_transactions_{column}", table_name="bank_transactions")
    op.drop_table("bank_transactions")

    for column in reversed(("firm_id", "client_id", "provider_name", "account_reference")):
        op.drop_index(
            f"ix_bank_import_batches_{column}",
            table_name="bank_import_batches",
        )
    op.drop_table("bank_import_batches")

    with op.batch_alter_table("review_outcomes") as batch_op:
        batch_op.drop_constraint("uq_review_outcomes_id_scope", type_="unique")
