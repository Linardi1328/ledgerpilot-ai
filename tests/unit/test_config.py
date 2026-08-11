from __future__ import annotations

import pytest
from pydantic import ValidationError

from ledgerpilot.core.config import (
    AuthMode,
    DocumentStorageBackend,
    Environment,
    MalwareScannerMode,
    Settings,
)


def test_development_settings_default_to_dev_auth_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "LEDGERPILOT_ENV",
        "LEDGERPILOT_DATABASE_URL",
        "LEDGERPILOT_LOG_LEVEL",
        "LEDGERPILOT_AUTH_MODE",
        "LEDGERPILOT_DEV_AUTH_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)
    assert settings.env is Environment.DEVELOPMENT
    assert settings.auth_mode is AuthMode.DISABLED
    assert not settings.dev_auth_enabled
    assert not settings.development_auth_is_enabled


def test_test_settings_can_enable_development_auth_explicitly() -> None:
    settings = Settings(
        env=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        auth_mode=AuthMode.DEVELOPMENT,
        dev_auth_enabled=True,
    )
    assert settings.development_auth_is_enabled


def test_development_auth_requires_explicit_enable_flag() -> None:
    with pytest.raises(ValidationError):
        Settings(
            env=Environment.TEST,
            database_url="sqlite+pysqlite:///:memory:",
            auth_mode=AuthMode.DEVELOPMENT,
            dev_auth_enabled=False,
        )


def test_development_auth_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            env=Environment.PRODUCTION,
            auth_mode=AuthMode.DEVELOPMENT,
            dev_auth_enabled=True,
        )


def test_development_malware_scanner_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            env=Environment.PRODUCTION,
            malware_scanner_mode=MalwareScannerMode.DEVELOPMENT,
        )


def test_local_document_storage_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            env=Environment.PRODUCTION,
            document_storage_backend=DocumentStorageBackend.LOCAL,
        )
