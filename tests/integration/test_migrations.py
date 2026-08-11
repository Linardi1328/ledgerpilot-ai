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
    "audit_events.occurred_at",
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
        assert tables == EXPECTED_PHASE_3_TABLES
    finally:
        engine.dispose()

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
