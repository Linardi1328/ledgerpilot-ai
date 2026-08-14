from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    VIEW_CONTEXT = "view_context"
    UPLOAD_DOCUMENTS = "upload_documents"
    VIEW_DOCUMENTS = "view_documents"
    RUN_EXTRACTION = "run_extraction"
    CORRECT_EXTRACTED_INFORMATION = "correct_extracted_information"
    RUN_ACCOUNTING_DECISION = "run_accounting_decision"
    REVIEW_RECOMMENDATIONS = "review_recommendations"
    APPROVE_ORDINARY_TRANSACTION = "approve_ordinary_transaction"
    APPROVE_HIGH_RISK_TRANSACTION = "approve_high_risk_transaction"
    REJECT_TRANSACTION = "reject_transaction"
    ESCALATE_TRANSACTION = "escalate_transaction"
    REQUEST_INFORMATION = "request_information"
    VIEW_AUDIT_HISTORY = "view_audit_history"
    MANAGE_USERS = "manage_users"
    MANAGE_CONFIGURATION = "manage_configuration"
    MANAGE_INTEGRATIONS = "manage_integrations"
    EXPORT_APPROVED_ENTRIES = "export_approved_entries"
    CORRECT_APPROVED_RECORDS = "correct_approved_records"
