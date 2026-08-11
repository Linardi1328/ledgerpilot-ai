from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from ledgerpilot.documents.types import (
    DetectedDocumentType,
    DocumentFailureCode,
    DocumentMediaType,
)

DOCUMENT_READ_CHUNK_BYTES = 64 * 1024
MAX_SUBMITTED_FILENAME_LENGTH = 255
PDF_SIGNATURE = b"%PDF-"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
MAX_SIGNATURE_BYTES = len(PNG_SIGNATURE)

_MEDIA_TYPE_EXTENSIONS: dict[DocumentMediaType, frozenset[str]] = {
    DocumentMediaType.PDF: frozenset({".pdf"}),
    DocumentMediaType.JPEG: frozenset({".jpg", ".jpeg"}),
    DocumentMediaType.PNG: frozenset({".png"}),
}


class DocumentValidationError(ValueError):
    def __init__(self, failure_code: DocumentFailureCode) -> None:
        self.failure_code = failure_code
        super().__init__(failure_code.value)


@dataclass(frozen=True)
class DocumentValidationResult:
    submitted_filename: str
    declared_media_type: DocumentMediaType
    detected_media_type: DocumentMediaType


def normalise_declared_media_type(value: str | None) -> DocumentMediaType:
    if value is None:
        raise DocumentValidationError(DocumentFailureCode.UNSUPPORTED_FILE_TYPE)
    media_type = value.split(";", 1)[0].strip().casefold()
    try:
        return DocumentMediaType(media_type)
    except ValueError as exc:
        raise DocumentValidationError(DocumentFailureCode.UNSUPPORTED_FILE_TYPE) from exc


def validate_submitted_filename(filename: str | None) -> str:
    if filename is None:
        raise DocumentValidationError(DocumentFailureCode.UNSAFE_FILENAME)
    submitted_filename = filename.strip()
    if not submitted_filename:
        raise DocumentValidationError(DocumentFailureCode.UNSAFE_FILENAME)
    if len(submitted_filename) > MAX_SUBMITTED_FILENAME_LENGTH:
        raise DocumentValidationError(DocumentFailureCode.UNSAFE_FILENAME)
    if "/" in submitted_filename or "\\" in submitted_filename:
        raise DocumentValidationError(DocumentFailureCode.UNSAFE_FILENAME)
    if submitted_filename in {".", ".."}:
        raise DocumentValidationError(DocumentFailureCode.UNSAFE_FILENAME)
    if any(ord(character) < 32 or ord(character) == 127 for character in submitted_filename):
        raise DocumentValidationError(DocumentFailureCode.UNSAFE_FILENAME)
    return submitted_filename


def detect_document_type(signature_bytes: bytes) -> DetectedDocumentType:
    if signature_bytes.startswith(PDF_SIGNATURE):
        return DetectedDocumentType(
            media_type=DocumentMediaType.PDF,
            allowed_extensions=_MEDIA_TYPE_EXTENSIONS[DocumentMediaType.PDF],
        )
    if signature_bytes.startswith(PNG_SIGNATURE):
        return DetectedDocumentType(
            media_type=DocumentMediaType.PNG,
            allowed_extensions=_MEDIA_TYPE_EXTENSIONS[DocumentMediaType.PNG],
        )
    if signature_bytes.startswith(JPEG_SIGNATURE):
        return DetectedDocumentType(
            media_type=DocumentMediaType.JPEG,
            allowed_extensions=_MEDIA_TYPE_EXTENSIONS[DocumentMediaType.JPEG],
        )
    raise DocumentValidationError(DocumentFailureCode.UNSUPPORTED_FILE_TYPE)


def validate_document_metadata(
    *,
    submitted_filename: str,
    declared_media_type: DocumentMediaType,
    signature_bytes: bytes,
) -> DocumentValidationResult:
    detected_type = detect_document_type(signature_bytes)
    if declared_media_type != detected_type.media_type:
        raise DocumentValidationError(DocumentFailureCode.CONTENT_TYPE_MISMATCH)

    extension = PurePath(submitted_filename).suffix.casefold()
    if extension not in detected_type.allowed_extensions:
        raise DocumentValidationError(DocumentFailureCode.EXTENSION_MISMATCH)

    return DocumentValidationResult(
        submitted_filename=submitted_filename,
        declared_media_type=declared_media_type,
        detected_media_type=detected_type.media_type,
    )
