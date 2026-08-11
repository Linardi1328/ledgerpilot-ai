from __future__ import annotations

from ledgerpilot.core.config import MalwareScannerMode, Settings
from ledgerpilot.scanning.protocol import MalwareScanner, MalwareScanResult, MalwareScanStatus
from ledgerpilot.storage.protocol import DocumentStorage, StorageError

_DEVELOPMENT_INFECTED_MARKER = b"LEDGERPILOT_TEST_MALWARE"
_DEVELOPMENT_ERROR_MARKER = b"LEDGERPILOT_TEST_SCANNER_ERROR"
_SCAN_CHUNK_BYTES = 64 * 1024


class DisabledMalwareScanner:
    scanner_name = "disabled"

    def scan_staged(self, *, storage: DocumentStorage, storage_key: str) -> MalwareScanResult:
        return MalwareScanResult(
            status=MalwareScanStatus.ERROR,
            safe_code="scanner_unavailable",
        )


class DevelopmentMalwareScanner:
    scanner_name = "development"

    def scan_staged(self, *, storage: DocumentStorage, storage_key: str) -> MalwareScanResult:
        try:
            with storage.open_staged_reader(storage_key) as staged_file:
                while chunk := staged_file.read(_SCAN_CHUNK_BYTES):
                    if _DEVELOPMENT_ERROR_MARKER in chunk:
                        return MalwareScanResult(
                            status=MalwareScanStatus.ERROR,
                            safe_code="scanner_error",
                        )
                    if _DEVELOPMENT_INFECTED_MARKER in chunk:
                        return MalwareScanResult(
                            status=MalwareScanStatus.INFECTED,
                            safe_code="malware_detected",
                        )
        except StorageError:
            return MalwareScanResult(
                status=MalwareScanStatus.ERROR,
                safe_code="scanner_storage_error",
            )

        return MalwareScanResult(status=MalwareScanStatus.CLEAN)


def get_malware_scanner(settings: Settings) -> MalwareScanner:
    if settings.malware_scanner_mode == MalwareScannerMode.DEVELOPMENT:
        return DevelopmentMalwareScanner()
    return DisabledMalwareScanner()
