from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from ledgerpilot.extraction.types import ExtractionProviderMetadata, ExtractionProviderResult


@dataclass(frozen=True)
class ExtractionRequestContext:
    firm_id: UUID
    client_id: UUID
    document_id: UUID
    document_file_id: UUID
    source_sha256: str
    media_type: str


class ExtractionProvider(Protocol):
    @property
    def metadata(self) -> ExtractionProviderMetadata:
        raise NotImplementedError

    def extract(
        self,
        *,
        source_file: BinaryIO,
        context: ExtractionRequestContext,
    ) -> ExtractionProviderResult:
        raise NotImplementedError
