from __future__ import annotations

from enum import StrEnum


class AuditEventType(StrEnum):
    INFRASTRUCTURE_EVENT = "infrastructure.event"
    AUTHENTICATION_CONTEXT_READ = "authentication.context_read"
    DOCUMENT_INTAKE_STARTED = "document_intake_started"
    DOCUMENT_VALIDATION_FAILED = "document_validation_failed"
    DOCUMENT_SCAN_FAILED = "document_scan_failed"
    DOCUMENT_QUARANTINED = "document_quarantined"
    DOCUMENT_STORED = "document_stored"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_SUCCEEDED = "extraction_succeeded"
    EXTRACTION_FAILED = "extraction_failed"
    EXTRACTION_CORRECTION_RECORDED = "extraction_correction_recorded"
