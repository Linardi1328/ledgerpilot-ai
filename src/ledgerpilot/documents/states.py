from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATION_FAILED = "validation_failed"
    SCAN_PENDING = "scan_pending"
    SCANNING = "scanning"
    SCAN_FAILED = "scan_failed"
    QUARANTINED = "quarantined"
    STORED = "stored"
    REJECTED = "rejected"


_ALLOWED_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.UPLOADED: frozenset({DocumentStatus.VALIDATING}),
    DocumentStatus.VALIDATING: frozenset(
        {
            DocumentStatus.VALIDATION_FAILED,
            DocumentStatus.SCAN_PENDING,
        }
    ),
    DocumentStatus.SCAN_PENDING: frozenset({DocumentStatus.SCANNING}),
    DocumentStatus.SCANNING: frozenset(
        {
            DocumentStatus.SCAN_FAILED,
            DocumentStatus.QUARANTINED,
            DocumentStatus.STORED,
        }
    ),
    DocumentStatus.VALIDATION_FAILED: frozenset({DocumentStatus.REJECTED}),
    DocumentStatus.SCAN_FAILED: frozenset({DocumentStatus.REJECTED}),
    DocumentStatus.QUARANTINED: frozenset({DocumentStatus.REJECTED}),
    DocumentStatus.STORED: frozenset(),
    DocumentStatus.REJECTED: frozenset(),
}


class InvalidDocumentTransition(ValueError):
    pass


def transition_document_status(
    current_status: DocumentStatus,
    next_status: DocumentStatus,
) -> DocumentStatus:
    if next_status not in _ALLOWED_TRANSITIONS[current_status]:
        raise InvalidDocumentTransition(
            f"invalid document transition: {current_status.value} -> {next_status.value}"
        )
    return next_status
