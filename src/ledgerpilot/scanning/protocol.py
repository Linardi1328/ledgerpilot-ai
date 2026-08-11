from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from ledgerpilot.storage.protocol import DocumentStorage


class MalwareScanStatus(StrEnum):
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"


@dataclass(frozen=True)
class MalwareScanResult:
    status: MalwareScanStatus
    safe_code: str | None = None


class MalwareScanner(Protocol):
    scanner_name: str

    def scan_staged(self, *, storage: DocumentStorage, storage_key: str) -> MalwareScanResult:
        raise NotImplementedError
