from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ExtractionFailureCode(StrEnum):
    SOURCE_NOT_ELIGIBLE = "source_not_eligible"
    SOURCE_FILE_MISSING = "source_file_missing"
    PROVIDER_DISABLED = "provider_disabled"
    PROVIDER_FAILED = "provider_failed"
    INVALID_PROVIDER_OUTPUT = "invalid_provider_output"
    PERSISTENCE_FAILED = "persistence_failed"


class ExtractionValueType(StrEnum):
    TEXT = "text"
    DECIMAL = "decimal"
    DATE = "date"
    INTEGER = "integer"
    BOOLEAN = "boolean"


@dataclass(frozen=True)
class ExtractionProviderMetadata:
    provider_name: str
    provider_version: str
    model_version: str | None
    extraction_schema_version: str


@dataclass(frozen=True)
class ProviderExtractedField:
    field_path: str
    value_type: ExtractionValueType | str
    raw_value: str
    normalized_value: str | None = None
    confidence: Decimal | str | None = None
    source_page_number: int | None = None
    source_locator: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ExtractionProviderResult:
    metadata: ExtractionProviderMetadata
    fields: Sequence[ProviderExtractedField]


@dataclass(frozen=True)
class ValidatedExtractedField:
    field_path: str
    value_type: ExtractionValueType
    raw_value: str
    normalized_value: str | None
    confidence: Decimal | None
    source_page_number: int | None
    source_locator: dict[str, Any] | None
