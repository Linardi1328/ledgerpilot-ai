from __future__ import annotations

import pytest

from ledgerpilot.documents.states import (
    DocumentStatus,
    InvalidDocumentTransition,
    transition_document_status,
)


def test_valid_document_lifecycle_transitions_succeed() -> None:
    status = transition_document_status(DocumentStatus.UPLOADED, DocumentStatus.VALIDATING)
    status = transition_document_status(status, DocumentStatus.SCAN_PENDING)
    status = transition_document_status(status, DocumentStatus.SCANNING)
    status = transition_document_status(status, DocumentStatus.STORED)

    assert status is DocumentStatus.STORED


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    [
        (DocumentStatus.UPLOADED, DocumentStatus.STORED),
        (DocumentStatus.SCAN_FAILED, DocumentStatus.STORED),
        (DocumentStatus.QUARANTINED, DocumentStatus.STORED),
        (DocumentStatus.STORED, DocumentStatus.VALIDATING),
    ],
)
def test_invalid_document_lifecycle_transitions_fail(
    current_status: DocumentStatus,
    next_status: DocumentStatus,
) -> None:
    with pytest.raises(InvalidDocumentTransition):
        transition_document_status(current_status, next_status)
