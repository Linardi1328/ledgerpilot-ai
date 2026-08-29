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
    ACCOUNTING_DECISION_STARTED = "accounting_decision_started"
    ACCOUNTING_DECISION_SUCCEEDED = "accounting_decision_succeeded"
    ACCOUNTING_DECISION_FAILED = "accounting_decision_failed"
    REVIEW_TASK_CREATED = "review_task_created"
    REVIEW_TASK_ESCALATED = "review_task_escalated"
    REVIEW_COMMENT_ADDED = "review_comment_added"
    REVIEW_INFORMATION_REQUESTED = "review_information_requested"
    REVIEW_INFORMATION_RESPONDED = "review_information_responded"
    REVIEW_TASK_APPROVED = "review_task_approved"
    REVIEW_TASK_REJECTED = "review_task_rejected"
    BANK_IMPORT_RECORDED = "bank_import_recorded"
    RECONCILIATION_MATCH_GENERATED = "reconciliation_match_generated"
