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


class DocumentStorageBackend(StrEnum):
    LOCAL = "local"


class MalwareScannerMode(StrEnum):
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
    document_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    document_storage_backend: DocumentStorageBackend = Field(default=DocumentStorageBackend.LOCAL)
    document_storage_root: str = Field(default="local_storage")
    malware_scanner_mode: MalwareScannerMode = Field(default=MalwareScannerMode.DISABLED)

    model_config = SettingsConfigDict(
        env_prefix="LEDGERPILOT_",
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> Settings:
        is_production = self.env == Environment.PRODUCTION
        uses_development_auth = self.auth_mode == AuthMode.DEVELOPMENT
        uses_local_storage = self.document_storage_backend == DocumentStorageBackend.LOCAL
        uses_development_scanner = self.malware_scanner_mode == MalwareScannerMode.DEVELOPMENT

        if is_production and (self.dev_auth_enabled or uses_development_auth):
            raise ValueError("development authentication cannot be enabled in production")
        if uses_development_auth and not self.dev_auth_enabled:
            raise ValueError(
                "development authentication requires LEDGERPILOT_DEV_AUTH_ENABLED=true"
            )
        if self.dev_auth_enabled and not uses_development_auth:
            raise ValueError(
                "LEDGERPILOT_DEV_AUTH_ENABLED=true requires LEDGERPILOT_AUTH_MODE=development"
            )
        if is_production and uses_local_storage:
            raise ValueError("local document storage cannot be used in production")
        if is_production and uses_development_scanner:
            raise ValueError("development malware scanner cannot be used in production")
        return self

    @property
    def development_auth_is_enabled(self) -> bool:
        return (
            self.dev_auth_enabled
            and self.auth_mode == AuthMode.DEVELOPMENT
            and self.env in {Environment.DEVELOPMENT, Environment.TEST}
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
