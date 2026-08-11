from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DocumentMediaType(StrEnum):
    PDF = "application/pdf"
    JPEG = "image/jpeg"
    PNG = "image/png"


class DocumentFailureCode(StrEnum):
    EMPTY_FILE = "empty_file"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    CONTENT_TYPE_MISMATCH = "content_type_mismatch"
    EXTENSION_MISMATCH = "extension_mismatch"
    UNSAFE_FILENAME = "unsafe_filename"
    MALWARE_DETECTED = "malware_detected"
    MALWARE_SCAN_FAILED = "malware_scan_failed"
    STORAGE_FAILED = "storage_failed"


class DocumentFileArea(StrEnum):
    ACCEPTED = "accepted"
    QUARANTINE = "quarantine"


@dataclass(frozen=True)
class DetectedDocumentType:
    media_type: DocumentMediaType
    allowed_extensions: frozenset[str]
