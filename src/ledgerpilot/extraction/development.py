from __future__ import annotations

from decimal import Decimal
from typing import BinaryIO

from ledgerpilot.core.config import ExtractionProviderMode, Settings
from ledgerpilot.extraction.protocol import ExtractionProvider, ExtractionRequestContext
from ledgerpilot.extraction.types import (
    ExtractionProviderMetadata,
    ExtractionProviderResult,
    ProviderExtractedField,
)


class DisabledExtractionProvider:
    @property
    def metadata(self) -> ExtractionProviderMetadata:
        return ExtractionProviderMetadata(
            provider_name="disabled",
            provider_version="0",
            model_version=None,
            extraction_schema_version="disabled",
        )

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        del source_file, context
        raise RuntimeError("extraction provider is disabled")


class DevelopmentExtractionProvider:
    """Deterministic synthetic provider for development and tests only."""

    def __init__(self, *, extraction_schema_version: str) -> None:
        self._metadata = ExtractionProviderMetadata(
            provider_name="development",
            provider_version="0.1.0",
            model_version=None,
            extraction_schema_version=extraction_schema_version,
        )

    @property
    def metadata(self) -> ExtractionProviderMetadata:
        return self._metadata

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        del context
        source_file.read(1)
        return ExtractionProviderResult(
            metadata=self._metadata,
            fields=(
                ProviderExtractedField(
                    field_path="document.type",
                    value_type="text",
                    raw_value="synthetic_purchase_invoice",
                    normalized_value="purchase_invoice",
                    confidence=Decimal("0.8800"),
                    source_page_number=1,
                    source_locator={"page": 1},
                ),
                ProviderExtractedField(
                    field_path="supplier.name",
                    value_type="text",
                    raw_value="Synthetic Office Supplies Sdn. Bhd.",
                    confidence=Decimal("0.8200"),
                    source_page_number=1,
                    source_locator={
                        "page": 1,
                        "bbox": {"x1": "0.10", "y1": "0.12", "x2": "0.70", "y2": "0.18"},
                    },
                ),
                ProviderExtractedField(
                    field_path="invoice.number",
                    value_type="text",
                    raw_value="SYN-INV-001",
                    normalized_value="SYN-INV-001",
                    confidence=Decimal("0.9100"),
                    source_page_number=1,
                ),
                ProviderExtractedField(
                    field_path="invoice.date",
                    value_type="date",
                    raw_value="2026-08-11",
                    normalized_value="2026-08-11",
                    confidence=Decimal("0.7900"),
                    source_page_number=1,
                ),
                ProviderExtractedField(
                    field_path="invoice.currency",
                    value_type="text",
                    raw_value="MYR",
                    normalized_value="MYR",
                    confidence=Decimal("0.8000"),
                    source_page_number=1,
                ),
                ProviderExtractedField(
                    field_path="invoice.total",
                    value_type="decimal",
                    raw_value="RM 100.00",
                    normalized_value="100.00",
                    confidence=Decimal("0.7100"),
                    source_page_number=1,
                ),
            ),
        )


def get_extraction_provider(settings: Settings) -> ExtractionProvider:
    if settings.extraction_provider == ExtractionProviderMode.DEVELOPMENT:
        return DevelopmentExtractionProvider(
            extraction_schema_version=settings.extraction_schema_version,
        )
    return DisabledExtractionProvider()
