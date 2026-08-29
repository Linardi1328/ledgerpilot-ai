from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import DateTime, create_engine, inspect

from alembic import command
from ledgerpilot.persistence.base import Base

EXPECTED_PHASE_3_TABLES = {
    "alembic_version",
    "audit_events",
    "client_access",
    "client_entities",
    "document_files",
    "documents",
    "extracted_fields",
    "extraction_field_corrections",
    "extraction_runs",
    "firm_memberships",
    "firms",
    "users",
}

EXPECTED_PHASE_4_TABLES = EXPECTED_PHASE_3_TABLES | {
    "accounting_decision_findings",
    "accounting_decision_runs",
    "accounting_duplicate_candidates",
    "accounting_recommendations",
    "accounting_supplier_match_candidates",
    "proposed_journal_lines",
    "proposed_journals",
}

EXPECTED_PHASE_5_FIRST_SLICE_TABLES = EXPECTED_PHASE_4_TABLES | {"review_tasks"}

EXPECTED_PHASE_5_TABLES = EXPECTED_PHASE_5_FIRST_SLICE_TABLES | {
    "review_comments",
    "review_outcomes",
}

EXPECTED_PHASE_6_TABLES = EXPECTED_PHASE_5_TABLES | {
    "bank_import_batches",
    "bank_transactions",
    "reconciliation_candidates",
    "reconciliation_match_runs",
}

EXPECTED_TABLES_AFTER_PHASE_3_DOWNGRADE = {
    "alembic_version",
    "audit_events",
    "client_access",
    "client_entities",
    "document_files",
    "documents",
    "firm_memberships",
    "firms",
    "users",
}

EXPECTED_TIMEZONE_AWARE_TIMESTAMP_COLUMNS = {
    "accounting_decision_findings.created_at",
    "accounting_decision_runs.created_at",
    "accounting_duplicate_candidates.created_at",
    "accounting_recommendations.created_at",
    "accounting_supplier_match_candidates.created_at",
    "audit_events.occurred_at",
    "bank_import_batches.created_at",
    "bank_transactions.created_at",
    "client_access.created_at",
    "client_entities.created_at",
    "client_entities.updated_at",
    "document_files.created_at",
    "documents.created_at",
    "documents.updated_at",
    "extracted_fields.created_at",
    "extraction_field_corrections.created_at",
    "extraction_runs.created_at",
    "firm_memberships.created_at",
    "firms.created_at",
    "firms.updated_at",
    "proposed_journal_lines.created_at",
    "proposed_journals.created_at",
    "reconciliation_candidates.created_at",
    "reconciliation_match_runs.created_at",
    "review_comments.created_at",
    "review_outcomes.created_at",
    "review_tasks.created_at",
    "review_tasks.updated_at",
    "users.created_at",
    "users.updated_at",
}


def test_initial_migration_upgrade_downgrade_and_schema(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "migration.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("LEDGERPILOT_ENV", "test")
    monkeypatch.setenv("LEDGERPILOT_DATABASE_URL", database_url)
    monkeypatch.setenv("LEDGERPILOT_AUTH_MODE", "disabled")
    monkeypatch.setenv("LEDGERPILOT_DEV_AUTH_ENABLED", "false")

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert tables == EXPECTED_PHASE_6_TABLES
        review_columns = {column["name"] for column in inspect(engine).get_columns("review_tasks")}
        assert "risk_class" in review_columns
    finally:
        engine.dispose()

    command.downgrade(config, "0006_phase_5_review")
    engine = create_engine(database_url)
    try:
        tables_after_phase_6_downgrade = set(inspect(engine).get_table_names())
        assert tables_after_phase_6_downgrade == EXPECTED_PHASE_5_TABLES
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    command.downgrade(config, "0005_phase_5")
    engine = create_engine(database_url)
    try:
        tables_after_completion_downgrade = set(inspect(engine).get_table_names())
        assert tables_after_completion_downgrade == EXPECTED_PHASE_5_FIRST_SLICE_TABLES
        review_columns = {column["name"] for column in inspect(engine).get_columns("review_tasks")}
        assert "risk_class" not in review_columns
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    command.downgrade(config, "0004_phase_4")
    engine = create_engine(database_url)
    try:
        tables_after_phase_5_downgrade = set(inspect(engine).get_table_names())
        assert tables_after_phase_5_downgrade == EXPECTED_PHASE_4_TABLES
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    command.downgrade(config, "0003_phase_3")
    engine = create_engine(database_url)
    try:
        tables_after_phase_4_downgrade = set(inspect(engine).get_table_names())
        assert tables_after_phase_4_downgrade == EXPECTED_PHASE_3_TABLES
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    command.downgrade(config, "0002_phase_2")
    engine = create_engine(database_url)
    try:
        tables_after_downgrade = set(inspect(engine).get_table_names())
        assert tables_after_downgrade == EXPECTED_TABLES_AFTER_PHASE_3_DOWNGRADE
    finally:
        engine.dispose()

    command.upgrade(config, "head")


def test_persistent_timestamp_metadata_is_timezone_aware() -> None:
    timestamp_columns: set[str] = set()
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.name in {"created_at", "updated_at", "occurred_at"}:
                timestamp_columns.add(f"{table.name}.{column.name}")
                assert isinstance(column.type, DateTime)
                assert column.type.timezone

    assert timestamp_columns == EXPECTED_TIMEZONE_AWARE_TIMESTAMP_COLUMNS
