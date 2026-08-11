from __future__ import annotations

import pytest
from pydantic import ValidationError

from ledgerpilot.core.config import AuthMode, Environment, Settings


def test_development_settings_default_to_dev_auth_disabled() -> None:
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
