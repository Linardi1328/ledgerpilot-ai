from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from ledgerpilot.extraction.types import (
    ExtractionProviderMetadata,
    ExtractionProviderResult,
    ExtractionValueType,
    ProviderExtractedField,
    ValidatedExtractedField,
)

FIELD_PATH_MAX_LENGTH = 255
SOURCE_LOCATOR_MAX_CHARS = 1000
FIELD_PATH_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*|\[[0-9]+])*$")
PROVIDER_CONTROLLED_PATH_PARTS = frozenset(
    {
        "client_id",
        "document_file_id",
        "document_id",
        "extraction_run_id",
        "firm_id",
        "membership_id",
        "run_id",
        "storage_key",
        "user_id",
    }
)


class ProviderOutputValidationError(ValueError):
    pass


def validate_provider_lineage(
    *,
    result_metadata: ExtractionProviderMetadata,
    expected_metadata: ExtractionProviderMetadata,
) -> None:
    if result_metadata != expected_metadata:
        raise ProviderOutputValidationError(
            "provider result lineage does not match expected run lineage"
        )


def validate_provider_result(
    result: ExtractionProviderResult,
    *,
    max_fields: int,
    max_value_chars: int,
) -> list[ValidatedExtractedField]:
    if max_fields <= 0:
        raise ValueError("max_fields must be positive")
    if max_value_chars <= 0:
        raise ValueError("max_value_chars must be positive")
    if len(result.fields) > max_fields:
        raise ProviderOutputValidationError("provider returned too many fields")

    paths: set[str] = set()
    validated: list[ValidatedExtractedField] = []
    for field in result.fields:
        validated_field = validate_provider_field(field, max_value_chars=max_value_chars)
        if validated_field.field_path in paths:
            raise ProviderOutputValidationError("provider returned duplicate field paths")
        paths.add(validated_field.field_path)
        validated.append(validated_field)
    return validated


def validate_provider_field(
    field: ProviderExtractedField,
    *,
    max_value_chars: int,
) -> ValidatedExtractedField:
    field_path = _validate_field_path(field.field_path)
    value_type = _validate_value_type(field.value_type)
    raw_value = _validate_value("raw_value", field.raw_value, max_value_chars=max_value_chars)
    normalized_value = _validate_optional_value(
        "normalized_value",
        field.normalized_value,
        max_value_chars=max_value_chars,
    )
    confidence = _validate_confidence(field.confidence)
    source_page_number = _validate_source_page_number(field.source_page_number)
    source_locator = _validate_source_locator(field.source_locator)
    _validate_normalized_value(value_type=value_type, normalized_value=normalized_value)
    return ValidatedExtractedField(
        field_path=field_path,
        value_type=value_type,
        raw_value=raw_value,
        normalized_value=normalized_value,
        confidence=confidence,
        source_page_number=source_page_number,
        source_locator=source_locator,
    )


def _validate_field_path(field_path: str) -> str:
    if not field_path:
        raise ProviderOutputValidationError("field path is required")
    if len(field_path) > FIELD_PATH_MAX_LENGTH:
        raise ProviderOutputValidationError("field path is too long")
    if FIELD_PATH_PATTERN.fullmatch(field_path) is None:
        raise ProviderOutputValidationError("field path has invalid format")
    parts = {part.strip("[]0123456789") for part in re.split(r"[.]", field_path)}
    if parts & PROVIDER_CONTROLLED_PATH_PARTS:
        raise ProviderOutputValidationError("field path attempts to set controlled identity")
    return field_path


def _validate_value_type(value_type: ExtractionValueType | str) -> ExtractionValueType:
    try:
        return ExtractionValueType(value_type)
    except ValueError as exc:
        raise ProviderOutputValidationError("value type is unsupported") from exc


def _validate_value(name: str, value: str, *, max_value_chars: int) -> str:
    if not isinstance(value, str):
        raise ProviderOutputValidationError(f"{name} must be a string")
    if len(value) > max_value_chars:
        raise ProviderOutputValidationError(f"{name} is too long")
    return value


def _validate_optional_value(
    name: str,
    value: str | None,
    *,
    max_value_chars: int,
) -> str | None:
    if value is None:
        return None
    return _validate_value(name, value, max_value_chars=max_value_chars)


def _validate_confidence(confidence: Decimal | str | None) -> Decimal | None:
    if confidence is None:
        return None
    if isinstance(confidence, float):
        raise ProviderOutputValidationError("confidence must not be a float")
    parsed = _parse_finite_decimal(str(confidence), error_message="confidence is invalid")
    if parsed < Decimal("0") or parsed > Decimal("1"):
        raise ProviderOutputValidationError("confidence is out of range")
    try:
        return parsed.quantize(Decimal("0.0001"))
    except InvalidOperation as exc:
        raise ProviderOutputValidationError("confidence is invalid") from exc


def _validate_source_page_number(source_page_number: int | None) -> int | None:
    if source_page_number is None:
        return None
    if isinstance(source_page_number, bool) or not isinstance(source_page_number, int):
        raise ProviderOutputValidationError("source page number must be an integer")
    if source_page_number < 1:
        raise ProviderOutputValidationError("source page number must be positive")
    return source_page_number


def _validate_source_locator(source_locator: Any) -> dict[str, Any] | None:
    if source_locator is None:
        return None
    if not isinstance(source_locator, dict):
        raise ProviderOutputValidationError("source locator must be an object")
    if len(source_locator) > 10:
        raise ProviderOutputValidationError("source locator is too large")
    locator = dict(source_locator)
    try:
        encoded = json.dumps(locator, sort_keys=True)
    except TypeError as exc:
        raise ProviderOutputValidationError("source locator is not JSON serializable") from exc
    if len(encoded) > SOURCE_LOCATOR_MAX_CHARS:
        raise ProviderOutputValidationError("source locator is too large")
    if "bbox" in locator:
        _validate_bbox(locator["bbox"])
    return locator


def _validate_bbox(bbox: Any) -> None:
    if not isinstance(bbox, dict):
        raise ProviderOutputValidationError("source locator bbox must be an object")
    expected_keys = {"x1", "y1", "x2", "y2"}
    if set(bbox) != expected_keys:
        raise ProviderOutputValidationError("source locator bbox has invalid shape")
    values = {key: _parse_unit_decimal(str(bbox[key])) for key in expected_keys}
    if values["x1"] > values["x2"] or values["y1"] > values["y2"]:
        raise ProviderOutputValidationError("source locator bbox bounds are invalid")


def _parse_unit_decimal(value: str) -> Decimal:
    parsed = _parse_finite_decimal(
        value,
        error_message="source locator coordinate is invalid",
    )
    if parsed < Decimal("0") or parsed > Decimal("1"):
        raise ProviderOutputValidationError("source locator coordinate is out of range")
    return parsed


def _validate_normalized_value(
    *,
    value_type: ExtractionValueType,
    normalized_value: str | None,
) -> None:
    if normalized_value is None:
        return
    if value_type == ExtractionValueType.DECIMAL:
        _parse_decimal(normalized_value)
    elif value_type == ExtractionValueType.DATE:
        _parse_iso_date(normalized_value)
    elif value_type == ExtractionValueType.INTEGER:
        _parse_integer(normalized_value)
    elif value_type == ExtractionValueType.BOOLEAN and normalized_value not in {"true", "false"}:
        raise ProviderOutputValidationError("normalized boolean must be true or false")


def _parse_decimal(value: str) -> Decimal:
    return _parse_finite_decimal(value, error_message="normalized decimal is invalid")


def _parse_finite_decimal(value: str, *, error_message: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ProviderOutputValidationError(error_message) from exc
    if not parsed.is_finite():
        raise ProviderOutputValidationError(error_message)
    return parsed


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ProviderOutputValidationError("normalized date is invalid") from exc


def _parse_integer(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ProviderOutputValidationError("normalized integer is invalid") from exc
