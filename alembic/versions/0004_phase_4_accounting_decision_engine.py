"""phase 4 accounting decision engine

Revision ID: 0004_phase_4
Revises: 0003_phase_3
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_phase_4"
down_revision: str | None = "0003_phase_3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounting_decision_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("initiated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("initiated_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("engine_name", sa.String(length=80), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=True),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'succeeded', 'failed')",
            name="ck_accounting_decision_runs_status",
        ),
        sa.CheckConstraint(
            "failure_code is null or failure_code in ("
            "'source_not_eligible', 'decision_engine_failed', 'persistence_failed'"
            ")",
            name="ck_accounting_decision_runs_failure_code",
        ),
        sa.CheckConstraint(
            "length(engine_name) > 0",
            name="ck_accounting_decision_runs_engine_name",
        ),
        sa.CheckConstraint(
            "length(engine_version) > 0",
            name="ck_accounting_decision_runs_engine_version",
        ),
        sa.CheckConstraint(
            "length(source_sha256) = 64",
            name="ck_accounting_decision_runs_source_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["client_id", "firm_id"],
            ["client_entities.id", "client_entities.firm_id"],
            name="fk_accounting_decision_runs_client_firm",
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"]),
        sa.ForeignKeyConstraint(
            ["document_id", "firm_id", "client_id"],
            ["documents.id", "documents.firm_id", "documents.client_id"],
            name="fk_accounting_decision_runs_document_scope",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id", "firm_id", "client_id", "document_id"],
            [
                "extraction_runs.id",
                "extraction_runs.firm_id",
                "extraction_runs.client_id",
                "extraction_runs.document_id",
            ],
            name="fk_accounting_decision_runs_extraction_scope",
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by_membership_id", "initiated_by_user_id", "firm_id"],
            ["firm_memberships.id", "firm_memberships.user_id", "firm_memberships.firm_id"],
            name="fk_accounting_decision_runs_initiator_membership_user_firm",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "firm_id",
            "client_id",
            "document_id",
            "extraction_run_id",
            name="uq_accounting_decision_runs_id_scope",
        ),
    )
    op.create_index(
        "ix_accounting_decision_runs_client_id",
        "accounting_decision_runs",
        ["client_id"],
    )
    op.create_index(
        "ix_accounting_decision_runs_document_id",
        "accounting_decision_runs",
        ["document_id"],
    )
    op.create_index(
        "ix_accounting_decision_runs_extraction_run_id",
        "accounting_decision_runs",
        ["extraction_run_id"],
    )
    op.create_index(
        "ix_accounting_decision_runs_firm_id",
        "accounting_decision_runs",
        ["firm_id"],
    )
    op.create_index(
        "ix_accounting_decision_runs_initiated_by_membership_id",
        "accounting_decision_runs",
        ["initiated_by_membership_id"],
    )
    op.create_index(
        "ix_accounting_decision_runs_initiated_by_user_id",
        "accounting_decision_runs",
        ["initiated_by_user_id"],
    )
    op.create_index(
        "ix_accounting_decision_runs_request_id",
        "accounting_decision_runs",
        ["request_id"],
    )
    op.create_index(
        "ix_accounting_decision_runs_status",
        "accounting_decision_runs",
        ["status"],
    )

    op.create_table(
        "accounting_decision_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("field_path", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "code in ("
            "'missing_required_field', 'arithmetic_mismatch', 'possible_duplicate', "
            "'new_supplier', 'low_extraction_confidence', 'unknown_account_mapping', "
            "'tax_review_required', 'unbalanced_journal'"
            ")",
            name="ck_accounting_decision_findings_code",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'warning', 'error')",
            name="ck_accounting_decision_findings_severity",
        ),
        sa.CheckConstraint(
            "field_path is null or length(field_path) > 0",
            name="ck_accounting_decision_findings_field_path",
        ),
        sa.CheckConstraint(
            "length(description) > 0",
            name="ck_accounting_decision_findings_description",
        ),
        _decision_run_scope_fk("fk_accounting_decision_findings_run_scope"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_decision_child_indexes("accounting_decision_findings", extra=("code",))

    op.create_table(
        "accounting_supplier_match_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_reference", sa.String(length=120), nullable=False),
        sa.Column("supplier_name", sa.String(length=200), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("explanation", sa.String(length=500), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("matcher_name", sa.String(length=80), nullable=False),
        sa.Column("matcher_version", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=True),
        sa.Column("is_confident", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_accounting_supplier_match_candidates_confidence",
        ),
        sa.CheckConstraint(
            "length(supplier_reference) > 0",
            name="ck_accounting_supplier_match_candidates_reference",
        ),
        sa.CheckConstraint(
            "length(supplier_name) > 0",
            name="ck_accounting_supplier_match_candidates_name",
        ),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_accounting_supplier_match_candidates_explanation",
        ),
        sa.CheckConstraint(
            "length(matcher_name) > 0",
            name="ck_accounting_supplier_match_candidates_matcher_name",
        ),
        sa.CheckConstraint(
            "length(matcher_version) > 0",
            name="ck_accounting_supplier_match_candidates_matcher_version",
        ),
        _decision_run_scope_fk("fk_accounting_supplier_match_candidates_run_scope"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "decision_run_id",
            "supplier_reference",
            name="uq_accounting_supplier_match_candidates_run_supplier",
        ),
    )
    _create_decision_child_indexes("accounting_supplier_match_candidates")

    op.create_table(
        "accounting_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_type", sa.String(length=40), nullable=False),
        sa.Column("recommended_value", sa.String(length=200), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("explanation", sa.String(length=500), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("rule_name", sa.String(length=80), nullable=False),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "recommendation_type in ('gl_account', 'tax_code', 'cost_centre', 'category')",
            name="ck_accounting_recommendations_type",
        ),
        sa.CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_accounting_recommendations_confidence",
        ),
        sa.CheckConstraint(
            "length(recommended_value) > 0",
            name="ck_accounting_recommendations_value",
        ),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_accounting_recommendations_explanation",
        ),
        sa.CheckConstraint(
            "length(rule_name) > 0",
            name="ck_accounting_recommendations_rule_name",
        ),
        sa.CheckConstraint(
            "length(rule_version) > 0",
            name="ck_accounting_recommendations_rule_version",
        ),
        _decision_run_scope_fk("fk_accounting_recommendations_run_scope"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_decision_child_indexes("accounting_recommendations", extra=("recommendation_type",))

    op.create_table(
        "proposed_journals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_debits", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("total_credits", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("balance_status", sa.String(length=20), nullable=False),
        sa.Column("is_balanced", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(currency) > 0", name="ck_proposed_journals_currency"),
        sa.CheckConstraint("total_debits >= 0", name="ck_proposed_journals_debits_nonnegative"),
        sa.CheckConstraint("total_credits >= 0", name="ck_proposed_journals_credits_nonnegative"),
        sa.CheckConstraint(
            "balance_status in ('balanced', 'unbalanced')",
            name="ck_proposed_journals_balance_status",
        ),
        sa.CheckConstraint(
            "(is_balanced = true and total_debits = total_credits) "
            "or (is_balanced = false and total_debits <> total_credits)",
            name="ck_proposed_journals_balance_consistency",
        ),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_proposed_journals_explanation",
        ),
        _decision_run_scope_fk("fk_proposed_journals_run_scope"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_run_id", name="uq_proposed_journals_decision_run"),
        sa.UniqueConstraint(
            "id",
            "decision_run_id",
            "firm_id",
            "client_id",
            "document_id",
            "extraction_run_id",
            name="uq_proposed_journals_id_scope",
        ),
    )
    _create_decision_child_indexes("proposed_journals")

    op.create_table(
        "accounting_duplicate_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_document_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("explanation", sa.String(length=500), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("detector_name", sa.String(length=80), nullable=False),
        sa.Column("detector_version", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_accounting_duplicate_candidates_confidence",
        ),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_accounting_duplicate_candidates_explanation",
        ),
        sa.CheckConstraint(
            "length(detector_name) > 0",
            name="ck_accounting_duplicate_candidates_detector_name",
        ),
        sa.CheckConstraint(
            "length(detector_version) > 0",
            name="ck_accounting_duplicate_candidates_detector_version",
        ),
        _decision_run_scope_fk("fk_accounting_duplicate_candidates_run_scope"),
        sa.ForeignKeyConstraint(
            ["candidate_document_id", "firm_id", "client_id"],
            ["documents.id", "documents.firm_id", "documents.client_id"],
            name="fk_accounting_duplicate_candidates_document_scope",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_extraction_run_id", "firm_id", "client_id", "candidate_document_id"],
            [
                "extraction_runs.id",
                "extraction_runs.firm_id",
                "extraction_runs.client_id",
                "extraction_runs.document_id",
            ],
            name="fk_accounting_duplicate_candidates_extraction_scope",
        ),
        sa.ForeignKeyConstraint(
            [
                "candidate_decision_run_id",
                "firm_id",
                "client_id",
                "candidate_document_id",
                "candidate_extraction_run_id",
            ],
            [
                "accounting_decision_runs.id",
                "accounting_decision_runs.firm_id",
                "accounting_decision_runs.client_id",
                "accounting_decision_runs.document_id",
                "accounting_decision_runs.extraction_run_id",
            ],
            name="fk_accounting_duplicate_candidates_decision_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "decision_run_id",
            "candidate_decision_run_id",
            name="uq_accounting_duplicate_candidates_run_candidate",
        ),
    )
    _create_decision_child_indexes("accounting_duplicate_candidates")

    op.create_table(
        "proposed_journal_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposed_journal_id", sa.Uuid(), nullable=False),
        sa.Column("decision_run_id", sa.Uuid(), nullable=False),
        sa.Column("firm_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("account_reference", sa.String(length=120), nullable=False),
        sa.Column("debit_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("credit_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("tax_code_reference", sa.String(length=120), nullable=True),
        sa.Column("cost_centre_reference", sa.String(length=120), nullable=True),
        sa.Column("explanation", sa.String(length=500), nullable=False),
        sa.Column("lineage", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("line_number >= 1", name="ck_proposed_journal_lines_line_number"),
        sa.CheckConstraint(
            "length(account_reference) > 0",
            name="ck_proposed_journal_lines_account",
        ),
        sa.CheckConstraint("debit_amount >= 0", name="ck_proposed_journal_lines_debit_nonnegative"),
        sa.CheckConstraint(
            "credit_amount >= 0",
            name="ck_proposed_journal_lines_credit_nonnegative",
        ),
        sa.CheckConstraint(
            "((debit_amount > 0 and credit_amount = 0) "
            "or (credit_amount > 0 and debit_amount = 0))",
            name="ck_proposed_journal_lines_single_sided_amount",
        ),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_proposed_journal_lines_explanation",
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
            name="fk_proposed_journal_lines_journal_scope",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposed_journal_id",
            "line_number",
            name="uq_proposed_journal_lines_journal_line",
        ),
    )
    _create_decision_child_indexes("proposed_journal_lines", extra=("proposed_journal_id",))


def downgrade() -> None:
    _drop_decision_child_indexes("proposed_journal_lines", extra=("proposed_journal_id",))
    op.drop_table("proposed_journal_lines")

    _drop_decision_child_indexes("accounting_duplicate_candidates")
    op.drop_table("accounting_duplicate_candidates")

    _drop_decision_child_indexes("proposed_journals")
    op.drop_table("proposed_journals")

    _drop_decision_child_indexes("accounting_recommendations", extra=("recommendation_type",))
    op.drop_table("accounting_recommendations")

    _drop_decision_child_indexes("accounting_supplier_match_candidates")
    op.drop_table("accounting_supplier_match_candidates")

    _drop_decision_child_indexes("accounting_decision_findings", extra=("code",))
    op.drop_table("accounting_decision_findings")

    op.drop_index("ix_accounting_decision_runs_status", table_name="accounting_decision_runs")
    op.drop_index("ix_accounting_decision_runs_request_id", table_name="accounting_decision_runs")
    op.drop_index(
        "ix_accounting_decision_runs_initiated_by_user_id",
        table_name="accounting_decision_runs",
    )
    op.drop_index(
        "ix_accounting_decision_runs_initiated_by_membership_id",
        table_name="accounting_decision_runs",
    )
    op.drop_index("ix_accounting_decision_runs_firm_id", table_name="accounting_decision_runs")
    op.drop_index(
        "ix_accounting_decision_runs_extraction_run_id",
        table_name="accounting_decision_runs",
    )
    op.drop_index("ix_accounting_decision_runs_document_id", table_name="accounting_decision_runs")
    op.drop_index("ix_accounting_decision_runs_client_id", table_name="accounting_decision_runs")
    op.drop_table("accounting_decision_runs")


def _decision_run_scope_fk(name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["decision_run_id", "firm_id", "client_id", "document_id", "extraction_run_id"],
        [
            "accounting_decision_runs.id",
            "accounting_decision_runs.firm_id",
            "accounting_decision_runs.client_id",
            "accounting_decision_runs.document_id",
            "accounting_decision_runs.extraction_run_id",
        ],
        name=name,
    )


def _create_decision_child_indexes(table_name: str, *, extra: tuple[str, ...] = ()) -> None:
    for column in (
        "decision_run_id",
        "firm_id",
        "client_id",
        "document_id",
        "extraction_run_id",
        *extra,
    ):
        op.create_index(f"ix_{table_name}_{column}", table_name, [column])


def _drop_decision_child_indexes(table_name: str, *, extra: tuple[str, ...] = ()) -> None:
    for column in reversed(
        (
            "decision_run_id",
            "firm_id",
            "client_id",
            "document_id",
            "extraction_run_id",
            *extra,
        )
    ):
        op.drop_index(f"ix_{table_name}_{column}", table_name=table_name)
