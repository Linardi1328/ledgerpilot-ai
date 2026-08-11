from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class AuthMode(StrEnum):
    DISABLED = "disabled"
    DEVELOPMENT = "development"


class Settings(BaseSettings):
    env: Environment = Field(default=Environment.DEVELOPMENT)
    database_url: str = Field(
        default="postgresql+psycopg://ledgerpilot_dev:fake_dev_password@127.0.0.1:5432/ledgerpilot_dev"
    )
    log_level: str = Field(default="INFO")
    auth_mode: AuthMode = Field(default=AuthMode.DISABLED)
    dev_auth_enabled: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_prefix="LEDGERPILOT_",
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> Settings:
        if self.env is Environment.PRODUCTION and (
            self.dev_auth_enabled or self.auth_mode is AuthMode.DEVELOPMENT
        ):
            raise ValueError("development authentication cannot be enabled in production")
        if self.auth_mode is AuthMode.DEVELOPMENT and not self.dev_auth_enabled:
            raise ValueError(
                "development authentication requires LEDGERPILOT_DEV_AUTH_ENABLED=true"
            )
        if self.dev_auth_enabled and self.auth_mode is not AuthMode.DEVELOPMENT:
            raise ValueError(
                "LEDGERPILOT_DEV_AUTH_ENABLED=true requires LEDGERPILOT_AUTH_MODE=development"
            )
        return self

    @property
    def development_auth_is_enabled(self) -> bool:
        return (
            self.dev_auth_enabled
            and self.auth_mode is AuthMode.DEVELOPMENT
            and self.env in {Environment.DEVELOPMENT, Environment.TEST}
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
