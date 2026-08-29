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


def test_auditor_remains_read_only_but_can_view_authorized_review_history() -> None:
    auditor = _principal(Role.AUDITOR)
    assert has_permission(auditor, Permission.VIEW_AUDIT_HISTORY)
    assert has_permission(auditor, Permission.VIEW_DOCUMENTS)
    assert has_permission(auditor, Permission.VIEW_REVIEW_TASK)
    assert has_permission(auditor, Permission.VIEW_REVIEW_HISTORY)
    assert not has_permission(auditor, Permission.CREATE_REVIEW_TASK)
    assert not has_permission(auditor, Permission.ADD_REVIEW_COMMENT)
    assert not has_permission(auditor, Permission.REJECT_TRANSACTION)
    assert not has_permission(auditor, Permission.RUN_EXTRACTION)
    assert not has_permission(auditor, Permission.RUN_ACCOUNTING_DECISION)
    assert not has_permission(auditor, Permission.CORRECT_EXTRACTED_INFORMATION)


def test_client_submitter_can_only_respond_to_information_requests_in_review_workflow() -> None:
    submitter = _principal(Role.CLIENT_SUBMITTER)
    assert has_permission(submitter, Permission.UPLOAD_DOCUMENTS)
    assert has_permission(submitter, Permission.VIEW_INFORMATION_REQUEST)
    assert has_permission(submitter, Permission.RESPOND_TO_INFORMATION_REQUEST)
    assert not has_permission(submitter, Permission.RUN_EXTRACTION)
    assert not has_permission(submitter, Permission.CREATE_REVIEW_TASK)
    assert not has_permission(submitter, Permission.VIEW_REVIEW_TASK)
    assert not has_permission(submitter, Permission.ADD_REVIEW_COMMENT)
    assert not has_permission(submitter, Permission.REQUEST_INFORMATION)
    assert not has_permission(submitter, Permission.VIEW_REVIEW_HISTORY)
    assert not has_permission(submitter, Permission.MANAGE_CONFIGURATION)


def test_accountant_and_senior_reviewer_have_review_workflow_permissions() -> None:
    for role in (Role.ACCOUNTANT, Role.SENIOR_REVIEWER):
        principal = _principal(role)
        assert has_permission(principal, Permission.RUN_EXTRACTION)
        assert has_permission(principal, Permission.RUN_ACCOUNTING_DECISION)
        assert has_permission(principal, Permission.CREATE_REVIEW_TASK)
        assert has_permission(principal, Permission.VIEW_REVIEW_TASK)
        assert has_permission(principal, Permission.ADD_REVIEW_COMMENT)
        assert has_permission(principal, Permission.VIEW_REVIEW_HISTORY)
        assert has_permission(principal, Permission.REQUEST_INFORMATION)
        assert has_permission(principal, Permission.REJECT_TRANSACTION)
        assert has_permission(principal, Permission.ESCALATE_TRANSACTION)


def test_only_senior_reviewer_has_high_risk_approval_permission() -> None:
    assert not has_permission(_principal(Role.ACCOUNTANT), Permission.APPROVE_HIGH_RISK_TRANSACTION)
    assert has_permission(
        _principal(Role.SENIOR_REVIEWER),
        Permission.APPROVE_HIGH_RISK_TRANSACTION,
    )
