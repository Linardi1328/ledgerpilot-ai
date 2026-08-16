from __future__ import annotations

import uuid

from ledgerpilot.identity.authorization import has_permission, permissions_for_role
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role


def _principal(role: Role) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        firm_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        role=role,
        authorized_client_ids=frozenset(),
        permissions=permissions_for_role(role),
    )


def test_permission_allowed() -> None:
    assert has_permission(_principal(Role.ACCOUNTANT), Permission.APPROVE_ORDINARY_TRANSACTION)


def test_permission_denied() -> None:
    assert not has_permission(_principal(Role.AUDITOR), Permission.UPLOAD_DOCUMENTS)


def test_firm_admin_is_not_implicit_allow_all_for_accounting_permissions() -> None:
    admin = _principal(Role.FIRM_ADMIN)
    assert has_permission(admin, Permission.MANAGE_USERS)
    assert not has_permission(admin, Permission.RUN_EXTRACTION)
    assert not has_permission(admin, Permission.RUN_ACCOUNTING_DECISION)
    assert not has_permission(admin, Permission.CREATE_REVIEW_TASK)
    assert not has_permission(admin, Permission.VIEW_REVIEW_TASK)
    assert not has_permission(admin, Permission.APPROVE_ORDINARY_TRANSACTION)
    assert not has_permission(admin, Permission.APPROVE_HIGH_RISK_TRANSACTION)
    assert not has_permission(admin, Permission.CORRECT_APPROVED_RECORDS)


def test_auditor_remains_read_only() -> None:
    auditor = _principal(Role.AUDITOR)
    assert has_permission(auditor, Permission.VIEW_AUDIT_HISTORY)
    assert has_permission(auditor, Permission.VIEW_DOCUMENTS)
    assert not has_permission(auditor, Permission.CREATE_REVIEW_TASK)
    assert not has_permission(auditor, Permission.VIEW_REVIEW_TASK)
    assert not has_permission(auditor, Permission.REJECT_TRANSACTION)
    assert not has_permission(auditor, Permission.RUN_EXTRACTION)
    assert not has_permission(auditor, Permission.RUN_ACCOUNTING_DECISION)
    assert not has_permission(auditor, Permission.CORRECT_EXTRACTED_INFORMATION)


def test_client_submitter_has_restricted_access() -> None:
    submitter = _principal(Role.CLIENT_SUBMITTER)
    assert has_permission(submitter, Permission.UPLOAD_DOCUMENTS)
    assert not has_permission(submitter, Permission.RUN_EXTRACTION)
    assert not has_permission(submitter, Permission.CREATE_REVIEW_TASK)
    assert not has_permission(submitter, Permission.VIEW_REVIEW_TASK)
    assert not has_permission(submitter, Permission.REQUEST_INFORMATION)
    assert not has_permission(submitter, Permission.VIEW_AUDIT_HISTORY)
    assert not has_permission(submitter, Permission.MANAGE_CONFIGURATION)


def test_accountant_and_senior_reviewer_can_run_extraction() -> None:
    assert has_permission(_principal(Role.ACCOUNTANT), Permission.RUN_EXTRACTION)
    assert has_permission(_principal(Role.SENIOR_REVIEWER), Permission.RUN_EXTRACTION)


def test_accountant_and_senior_reviewer_can_run_accounting_decisions() -> None:
    assert has_permission(_principal(Role.ACCOUNTANT), Permission.RUN_ACCOUNTING_DECISION)
    assert has_permission(_principal(Role.SENIOR_REVIEWER), Permission.RUN_ACCOUNTING_DECISION)


def test_only_accountant_and_senior_reviewer_can_use_review_task_boundaries() -> None:
    for role in (Role.ACCOUNTANT, Role.SENIOR_REVIEWER):
        principal = _principal(role)
        assert has_permission(principal, Permission.CREATE_REVIEW_TASK)
        assert has_permission(principal, Permission.VIEW_REVIEW_TASK)

    for role in (Role.FIRM_ADMIN, Role.CLIENT_SUBMITTER, Role.AUDITOR):
        principal = _principal(role)
        assert not has_permission(principal, Permission.CREATE_REVIEW_TASK)
        assert not has_permission(principal, Permission.VIEW_REVIEW_TASK)
