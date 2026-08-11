from __future__ import annotations

import pytest

from ledgerpilot.documents.types import DocumentFailureCode, DocumentMediaType
from ledgerpilot.documents.validation import (
    DocumentValidationError,
    detect_document_type,
    normalise_declared_media_type,
    validate_document_metadata,
    validate_submitted_filename,
)

PDF_BYTES = b"%PDF-1.4\n% synthetic pdf\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\nsynthetic png"
JPEG_BYTES = b"\xff\xd8\xff\xe0synthetic jpeg"


@pytest.mark.parametrize(
    ("content", "expected_media_type"),
    [
        (PDF_BYTES, DocumentMediaType.PDF),
        (PNG_BYTES, DocumentMediaType.PNG),
        (JPEG_BYTES, DocumentMediaType.JPEG),
    ],
)
def test_supported_file_signatures_are_detected(
    content: bytes,
    expected_media_type: DocumentMediaType,
) -> None:
    assert detect_document_type(content).media_type is expected_media_type


def test_unsupported_signature_is_rejected() -> None:
    with pytest.raises(DocumentValidationError) as exc_info:
        detect_document_type(b"not a supported document")

    assert exc_info.value.failure_code is DocumentFailureCode.UNSUPPORTED_FILE_TYPE


def test_valid_pdf_metadata_is_accepted() -> None:
    result = validate_document_metadata(
        submitted_filename="invoice.pdf",
        declared_media_type=DocumentMediaType.PDF,
        signature_bytes=PDF_BYTES,
    )

    assert result.detected_media_type is DocumentMediaType.PDF


def test_mime_mismatch_is_rejected() -> None:
    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document_metadata(
            submitted_filename="invoice.pdf",
            declared_media_type=DocumentMediaType.PDF,
            signature_bytes=PNG_BYTES,
        )

    assert exc_info.value.failure_code is DocumentFailureCode.CONTENT_TYPE_MISMATCH


def test_extension_mismatch_is_rejected() -> None:
    with pytest.raises(DocumentValidationError) as exc_info:
        validate_document_metadata(
            submitted_filename="invoice.jpg",
            declared_media_type=DocumentMediaType.PDF,
            signature_bytes=PDF_BYTES,
        )

    assert exc_info.value.failure_code is DocumentFailureCode.EXTENSION_MISMATCH


def test_declared_media_type_must_be_allowlisted() -> None:
    with pytest.raises(DocumentValidationError) as exc_info:
        normalise_declared_media_type("application/vnd.ms-excel")

    assert exc_info.value.failure_code is DocumentFailureCode.UNSUPPORTED_FILE_TYPE


@pytest.mark.parametrize(
    "filename",
    [
        "../../secret.pdf",
        "..\\..\\secret.pdf",
        "folder/invoice.pdf",
        "folder\\invoice.pdf",
        "/tmp/invoice.pdf",
        "C:\\temp\\invoice.pdf",
        "x" * 256 + ".pdf",
        "invoice\x00.pdf",
        "invoice\n.pdf",
    ],
)
def test_unsafe_submitted_filenames_are_rejected(filename: str) -> None:
    with pytest.raises(DocumentValidationError) as exc_info:
        validate_submitted_filename(filename)

    assert exc_info.value.failure_code is DocumentFailureCode.UNSAFE_FILENAME


def test_safe_submitted_filename_is_preserved() -> None:
    assert validate_submitted_filename("Synthetic Invoice.PDF") == "Synthetic Invoice.PDF"
