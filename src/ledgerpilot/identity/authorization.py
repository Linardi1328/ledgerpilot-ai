from __future__ import annotations

from uuid import UUID

from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.FIRM_ADMIN: frozenset(
        {
            Permission.VIEW_CONTEXT,
            Permission.MANAGE_USERS,
            Permission.MANAGE_CONFIGURATION,
            Permission.MANAGE_INTEGRATIONS,
            Permission.VIEW_AUDIT_HISTORY,
        }
    ),
    Role.ACCOUNTANT: frozenset(
        {
            Permission.VIEW_CONTEXT,
            Permission.UPLOAD_DOCUMENTS,
            Permission.VIEW_DOCUMENTS,
            Permission.RUN_EXTRACTION,
            Permission.CORRECT_EXTRACTED_INFORMATION,
            Permission.RUN_ACCOUNTING_DECISION,
            Permission.REVIEW_RECOMMENDATIONS,
            Permission.CREATE_REVIEW_TASK,
            Permission.VIEW_REVIEW_TASK,
            Permission.ADD_REVIEW_COMMENT,
            Permission.VIEW_REVIEW_HISTORY,
            Permission.APPROVE_ORDINARY_TRANSACTION,
            Permission.REJECT_TRANSACTION,
            Permission.ESCALATE_TRANSACTION,
            Permission.REQUEST_INFORMATION,
            Permission.VIEW_AUDIT_HISTORY,
            Permission.IMPORT_BANK_TRANSACTIONS,
            Permission.VIEW_BANK_TRANSACTIONS,
            Permission.RUN_RECONCILIATION_MATCHING,
            Permission.VIEW_RECONCILIATION_MATCHES,
            Permission.EXPORT_APPROVED_ENTRIES,
        }
    ),
    Role.SENIOR_REVIEWER: frozenset(
        {
            Permission.VIEW_CONTEXT,
            Permission.UPLOAD_DOCUMENTS,
            Permission.VIEW_DOCUMENTS,
            Permission.RUN_EXTRACTION,
            Permission.CORRECT_EXTRACTED_INFORMATION,
            Permission.RUN_ACCOUNTING_DECISION,
            Permission.REVIEW_RECOMMENDATIONS,
            Permission.CREATE_REVIEW_TASK,
            Permission.VIEW_REVIEW_TASK,
            Permission.ADD_REVIEW_COMMENT,
            Permission.VIEW_REVIEW_HISTORY,
            Permission.APPROVE_ORDINARY_TRANSACTION,
            Permission.APPROVE_HIGH_RISK_TRANSACTION,
            Permission.REJECT_TRANSACTION,
            Permission.ESCALATE_TRANSACTION,
            Permission.REQUEST_INFORMATION,
            Permission.VIEW_AUDIT_HISTORY,
            Permission.IMPORT_BANK_TRANSACTIONS,
            Permission.VIEW_BANK_TRANSACTIONS,
            Permission.RUN_RECONCILIATION_MATCHING,
            Permission.VIEW_RECONCILIATION_MATCHES,
            Permission.EXPORT_APPROVED_ENTRIES,
            Permission.CORRECT_APPROVED_RECORDS,
        }
    ),
    Role.CLIENT_SUBMITTER: frozenset(
        {
            Permission.VIEW_CONTEXT,
            Permission.UPLOAD_DOCUMENTS,
            Permission.VIEW_DOCUMENTS,
            Permission.VIEW_INFORMATION_REQUEST,
            Permission.RESPOND_TO_INFORMATION_REQUEST,
        }
    ),
    Role.AUDITOR: frozenset(
        {
            Permission.VIEW_CONTEXT,
            Permission.VIEW_DOCUMENTS,
            Permission.REVIEW_RECOMMENDATIONS,
            Permission.VIEW_REVIEW_TASK,
            Permission.VIEW_REVIEW_HISTORY,
            Permission.VIEW_AUDIT_HISTORY,
            Permission.VIEW_BANK_TRANSACTIONS,
            Permission.VIEW_RECONCILIATION_MATCHES,
        }
    ),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def has_permission(principal: Principal, permission: Permission) -> bool:
    return permission in principal.permissions


def has_client_access(principal: Principal, client_id: UUID) -> bool:
    return client_id in principal.authorized_client_ids
