from __future__ import annotations

from decimal import Decimal

import pytest

from ledgerpilot.extraction.types import (
    ExtractionProviderMetadata,
    ExtractionProviderResult,
    ProviderExtractedField,
)
from ledgerpilot.extraction.validation import (
    ProviderOutputValidationError,
    validate_provider_lineage,
    validate_provider_result,
)


def _result(*fields: ProviderExtractedField) -> ExtractionProviderResult:
    return ExtractionProviderResult(
        metadata=_metadata(),
        fields=fields,
    )


def _metadata(
    *,
    provider_name: str = "development",
    provider_version: str = "0.1.0",
    model_version: str | None = None,
    extraction_schema_version: str = "ledgerpilot.extraction.v1",
) -> ExtractionProviderMetadata:
    return ExtractionProviderMetadata(
        provider_name=provider_name,
        provider_version=provider_version,
        model_version=model_version,
        extraction_schema_version=extraction_schema_version,
    )


def test_provider_lineage_metadata_must_match_authoritative_run_metadata() -> None:
    with pytest.raises(ProviderOutputValidationError):
        validate_provider_lineage(
            result_metadata=_metadata(model_version="synthetic-other-model"),
            expected_metadata=_metadata(model_version="synthetic-run-model"),
        )


def test_valid_provider_output_is_normalized_without_float_money() -> None:
    fields = validate_provider_result(
        _result(
            ProviderExtractedField(
                field_path="invoice.total",
                value_type="decimal",
                raw_value="RM 100.00",
                normalized_value="100.00",
                confidence=Decimal("0.71009"),
                source_page_number=1,
                source_locator={"page": 1, "bbox": {"x1": "0", "y1": "0", "x2": "1", "y2": "1"}},
            )
        ),
        max_fields=10,
        max_value_chars=4000,
    )

    assert fields[0].normalized_value == "100.00"
    assert fields[0].confidence == Decimal("0.7101")
    assert not isinstance(fields[0].confidence, float)


@pytest.mark.parametrize(
    "field",
    [
        ProviderExtractedField(field_path="", value_type="text", raw_value="x"),
        ProviderExtractedField(field_path="Firm.ID", value_type="text", raw_value="x"),
        ProviderExtractedField(field_path="firm_id", value_type="text", raw_value="x"),
        ProviderExtractedField(field_path="invoice.total", value_type="money", raw_value="x"),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="x",
            normalized_value="not-decimal",
        ),
        ProviderExtractedField(
            field_path="invoice.date",
            value_type="date",
            raw_value="01/02/2026",
            normalized_value="01/02/2026",
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="x",
            confidence=Decimal("1.1"),
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="x",
            source_page_number=0,
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="x",
            source_locator={"bbox": {"x1": "0.8", "y1": "0", "x2": "0.2", "y2": "1"}},
        ),
    ],
)
def test_invalid_provider_output_is_rejected(field: ProviderExtractedField) -> None:
    with pytest.raises(ProviderOutputValidationError):
        validate_provider_result(_result(field), max_fields=10, max_value_chars=4000)


@pytest.mark.parametrize(
    "field",
    [
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="RM NaN",
            normalized_value="NaN",
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="RM Infinity",
            normalized_value="Infinity",
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="RM -Infinity",
            normalized_value="-Infinity",
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="RM 100.00",
            normalized_value="100.00",
            confidence=Decimal("NaN"),
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="RM 100.00",
            normalized_value="100.00",
            confidence="Infinity",
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="RM 100.00",
            normalized_value="100.00",
            source_locator={"bbox": {"x1": "NaN", "y1": "0", "x2": "1", "y2": "1"}},
        ),
        ProviderExtractedField(
            field_path="invoice.total",
            value_type="decimal",
            raw_value="RM 100.00",
            normalized_value="100.00",
            source_locator={"bbox": {"x1": "0", "y1": "0", "x2": "Infinity", "y2": "1"}},
        ),
    ],
)
def test_non_finite_decimal_provider_values_are_rejected(field: ProviderExtractedField) -> None:
    with pytest.raises(ProviderOutputValidationError):
        validate_provider_result(_result(field), max_fields=10, max_value_chars=4000)


def test_duplicate_field_path_is_rejected() -> None:
    with pytest.raises(ProviderOutputValidationError):
        validate_provider_result(
            _result(
                ProviderExtractedField(
                    field_path="invoice.number", value_type="text", raw_value="A"
                ),
                ProviderExtractedField(
                    field_path="invoice.number", value_type="text", raw_value="B"
                ),
            ),
            max_fields=10,
            max_value_chars=4000,
        )


def test_excessive_provider_output_is_rejected() -> None:
    with pytest.raises(ProviderOutputValidationError):
        validate_provider_result(
            _result(
                ProviderExtractedField(
                    field_path="invoice.number", value_type="text", raw_value="A"
                ),
                ProviderExtractedField(
                    field_path="invoice.total", value_type="decimal", raw_value="B"
                ),
            ),
            max_fields=1,
            max_value_chars=4000,
        )


def test_excessive_value_length_is_rejected() -> None:
    with pytest.raises(ProviderOutputValidationError):
        validate_provider_result(
            _result(
                ProviderExtractedField(
                    field_path="invoice.number",
                    value_type="text",
                    raw_value="x" * 11,
                )
            ),
            max_fields=10,
            max_value_chars=10,
        )
