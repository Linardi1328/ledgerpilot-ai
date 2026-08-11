from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

EXPECTED_PHASE_1_TABLES = {
    "alembic_version",
    "audit_events",
    "client_access",
    "client_entities",
    "firm_memberships",
    "firms",
    "users",
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
        assert tables == EXPECTED_PHASE_1_TABLES
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    command.upgrade(config, "head")
