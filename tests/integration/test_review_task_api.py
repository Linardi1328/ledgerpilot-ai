from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ledgerpilot.accounting.rules import SyntheticAccountingDecisionPolicy
from ledgerpilot.api.app import create_app
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.core.config import Settings
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.accounting import AccountingDecisionRun
from ledgerpilot.persistence.repositories.audit import AuditRepository
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from ledgerpilot.storage.local import LocalDocumentStorage
from tests.conftest import IdentitySeed
from tests.integration.test_accounting_decision_api import (
    _auth_headers,
    _decision_url,
    _start_decision,
    _start_extraction,
    _upload_document,
)


def test_ordinary_review_is_human_approved_and_immutable(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    created = client.post(
        review_url,
        headers=_auth_headers(identity_seed, request_id="req-phase5-create"),
        json={},
    )
    assert created.status_code == 201
    task = created.json()
    assert task["status"] == "open"
    assert task["risk_class"] == "ordinary"
    assert task["escalation_state"] == "none"
    assert task["owner_membership_id"] == str(identity_seed.accountant_membership.id)

    listed = client.get(review_url, headers=_auth_headers(identity_seed))
    fetched = client.get(
        f"{review_url}/{task['id']}",
        headers=_auth_headers(identity_seed),
    )
    duplicate = client.post(review_url, headers=_auth_headers(identity_seed), json={})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [task["id"]]
    assert fetched.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "review_task_exists"

    approved = client.post(
        f"{review_url}/{task['id']}/approve",
        headers=_auth_headers(identity_seed, request_id="req-phase5-approve"),
        json={"note": "Synthetic ordinary human approval."},
    )
    assert approved.status_code == 200
    assert approved.json()["task"]["status"] == "approved"
    assert approved.json()["outcome"]["outcome_type"] == "approved"
    assert approved.json()["outcome"]["proposed_journal_id"] is not None
    assert approved.json()["outcome"]["source_correction_count"] == 0

    decision = db_session.get(AccountingDecisionRun, decision_run_id)
    assert decision is not None
    assert decision.status == "succeeded"

    events = _review_events(db_session, identity_seed, task["id"])
    assert [event.event_type for event in events] == [
        AuditEventType.REVIEW_TASK_CREATED.value,
        AuditEventType.REVIEW_TASK_APPROVED.value,
    ]
    assert all(
        "Synthetic ordinary human approval." not in str(event.metadata_json) for event in events
    )

    second_approval = client.post(
        f"{review_url}/{task['id']}/approve",
        headers=_auth_headers(identity_seed),
        json={},
    )
    terminal_comment = client.post(
        f"{review_url}/{task['id']}/comments",
        headers=_auth_headers(identity_seed),
        json={"body": "Should remain immutable."},
    )
    assert second_approval.status_code == 409
    assert second_approval.json()["error"]["code"] == "review_task_terminal"
    assert terminal_comment.status_code == 409
    assert terminal_comment.json()["error"]["code"] == "review_task_terminal"


def test_high_risk_review_requires_assigned_senior_approval(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    _create_decision(client, identity_seed, filename="synthetic-first.pdf")
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
        filename="synthetic-duplicate.pdf",
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    created = client.post(review_url, headers=_auth_headers(identity_seed), json={})
    assert created.status_code == 201
    task = created.json()
    assert task["risk_class"] == "senior_review_required"

    accountant_approval = client.post(
        f"{review_url}/{task['id']}/approve",
        headers=_auth_headers(identity_seed),
        json={},
    )
    assert accountant_approval.status_code == 403
    assert accountant_approval.json()["error"]["code"] == "senior_review_required"

    senior, membership = _add_senior(
        db_session,
        identity_seed,
        subject="dev-phase5-senior-approval",
    )
    wrong_target = client.post(
        f"{review_url}/{task['id']}/escalations",
        headers=_auth_headers(identity_seed),
        json={
            "senior_membership_id": str(identity_seed.accountant_membership.id),
            "reason": "Synthetic invalid escalation target.",
        },
    )
    assert wrong_target.status_code == 422
    assert wrong_target.json()["error"]["code"] == "invalid_review_owner"

    escalated = client.post(
        f"{review_url}/{task['id']}/escalations",
        headers=_auth_headers(identity_seed, request_id="req-phase5-escalate"),
        json={
            "senior_membership_id": str(membership.id),
            "reason": "Synthetic duplicate requires senior review.",
        },
    )
    assert escalated.status_code == 200
    assert escalated.json()["status"] == "escalated"
    assert escalated.json()["escalation_state"] == "senior_review"
    assert escalated.json()["owner_membership_id"] == str(membership.id)

    old_owner_approval = client.post(
        f"{review_url}/{task['id']}/approve",
        headers=_auth_headers(identity_seed),
        json={},
    )
    assert old_owner_approval.status_code == 403
    assert old_owner_approval.json()["error"]["code"] == "review_task_not_owned"

    approved = client.post(
        f"{review_url}/{task['id']}/approve",
        headers=_auth_headers(identity_seed, subject=senior.external_subject),
        json={},
    )
    assert approved.status_code == 200
    assert approved.json()["task"]["status"] == "approved"

    history = client.get(
        f"{review_url}/{task['id']}/history",
        headers=_auth_headers(identity_seed, subject=senior.external_subject),
    )
    assert history.status_code == 200
    assert history.json()["comments"][0]["kind"] == "escalation_reason"
    assert history.json()["comments"][0]["body"] == ("Synthetic duplicate requires senior review.")
    assert {event["event_type"] for event in history.json()["audit_events"]} >= {
        AuditEventType.REVIEW_TASK_CREATED.value,
        AuditEventType.REVIEW_TASK_ESCALATED.value,
        AuditEventType.REVIEW_TASK_APPROVED.value,
    }


def test_blocked_review_cannot_be_approved(
    settings: Settings,
    session_factory: sessionmaker[Session],
    document_storage: LocalDocumentStorage,
    identity_seed: IdentitySeed,
) -> None:
    policy = SyntheticAccountingDecisionPolicy(
        synthetic_journal_credit_adjustment=Decimal("0.01"),
    )
    with TestClient(
        create_app(
            settings=settings,
            session_factory=session_factory,
            document_storage=document_storage,
            accounting_decision_policy=policy,
        )
    ) as test_client:
        document_id, extraction_run_id, decision_run_id, _ = _create_decision(
            test_client,
            identity_seed,
        )
        review_url = _review_url(
            identity_seed.client_a.id,
            document_id,
            extraction_run_id,
            decision_run_id,
        )
        created = test_client.post(review_url, headers=_auth_headers(identity_seed), json={})
        assert created.status_code == 201
        assert created.json()["risk_class"] == "blocked"
        approved = test_client.post(
            f"{review_url}/{created.json()['id']}/approve",
            headers=_auth_headers(identity_seed),
            json={},
        )
    assert approved.status_code == 409
    assert approved.json()["error"]["code"] == "review_approval_blocked"


def test_corrections_are_attributed_and_stale_decisions_fail_closed(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id = _upload_document(client, identity_seed, filename="synthetic-corrected.pdf")
    extraction = _start_extraction(client, identity_seed, document_id=document_id)
    assert extraction.status_code == 201
    extraction_payload = extraction.json()
    extraction_run_id = UUID(extraction_payload["id"])
    total_field = next(
        field for field in extraction_payload["fields"] if field["field_path"] == "invoice.total"
    )
    before = _correct_field(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        field_id=UUID(total_field["id"]),
        normalized_value="101.00",
        request_id="req-phase5-correction-before",
    )
    assert before.status_code == 201
    decision = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
    )
    assert decision.status_code == 201
    decision_run_id = UUID(decision.json()["id"])
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    created = client.post(review_url, headers=_auth_headers(identity_seed), json={})
    approved = client.post(
        f"{review_url}/{created.json()['id']}/approve",
        headers=_auth_headers(identity_seed),
        json={},
    )
    assert approved.status_code == 200
    assert approved.json()["outcome"]["outcome_type"] == "corrected_and_approved"
    assert approved.json()["outcome"]["source_correction_count"] == 1

    post_approval_correction = _correct_field(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        field_id=UUID(total_field["id"]),
        normalized_value="103.00",
        request_id="req-phase5-correction-after-approval",
    )
    assert post_approval_correction.status_code == 409
    assert post_approval_correction.json()["error"]["code"] == "approved_record_locked"

    stale_document, stale_extraction, stale_decision, stale_payload = _create_decision(
        client,
        identity_seed,
        filename="synthetic-stale.pdf",
    )
    stale_url = _review_url(
        identity_seed.client_a.id,
        stale_document,
        stale_extraction,
        stale_decision,
    )
    stale_task = client.post(stale_url, headers=_auth_headers(identity_seed), json={}).json()
    stale_field = next(
        field for field in stale_payload["fields"] if field["field_path"] == "invoice.total"
    )
    after = _correct_field(
        client,
        identity_seed,
        document_id=stale_document,
        extraction_run_id=stale_extraction,
        field_id=UUID(stale_field["id"]),
        normalized_value="102.00",
        request_id="req-phase5-correction-after",
    )
    assert after.status_code == 201
    stale_approval = client.post(
        f"{stale_url}/{stale_task['id']}/approve",
        headers=_auth_headers(identity_seed),
        json={},
    )
    assert stale_approval.status_code == 409
    assert stale_approval.json()["error"]["code"] == "decision_stale_after_correction"


def test_information_exchange_is_client_scoped_and_audit_metadata_is_safe(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
        filename="synthetic-information.pdf",
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    task_id = client.post(review_url, headers=_auth_headers(identity_seed), json={}).json()["id"]
    requested = client.post(
        f"{review_url}/{task_id}/information-requests",
        headers=_auth_headers(identity_seed, request_id="req-phase5-info-request"),
        json={"body": "Please confirm the synthetic supporting reference."},
    )
    assert requested.status_code == 201
    assert requested.json()["task"]["status"] == "information_requested"

    submitter_headers = _auth_headers(
        identity_seed,
        subject=identity_seed.submitter.external_subject,
    )
    visible_request = client.get(
        f"{review_url}/{task_id}/information-request",
        headers=submitter_headers,
    )
    assert visible_request.status_code == 200
    assert visible_request.json()["kind"] == "information_request"
    assert visible_request.json()["body"] == ("Please confirm the synthetic supporting reference.")
    blocked = client.post(
        f"{review_url}/{task_id}/approve",
        headers=_auth_headers(identity_seed),
        json={},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "information_response_required"

    cross_client = client.post(
        _review_url(
            identity_seed.client_b.id,
            document_id,
            extraction_run_id,
            decision_run_id,
        )
        + f"/{task_id}/information-responses",
        headers=submitter_headers,
        json={"body": "Synthetic cross-client response."},
    )
    assert cross_client.status_code == 403
    responded = client.post(
        f"{review_url}/{task_id}/information-responses",
        headers=submitter_headers,
        json={"body": "Confirmed against the synthetic support document."},
    )
    assert responded.status_code == 201
    assert responded.json()["task"]["status"] == "open"
    comment = client.post(
        f"{review_url}/{task_id}/comments",
        headers=_auth_headers(identity_seed),
        json={"body": "Synthetic reviewer note after information response."},
    )
    assert comment.status_code == 201

    history = client.get(
        f"{review_url}/{task_id}/history",
        headers=_auth_headers(identity_seed),
    )
    assert history.status_code == 200
    assert [item["kind"] for item in history.json()["comments"]] == [
        "information_request",
        "information_response",
        "comment",
    ]
    audit_text = " ".join(
        str(event.metadata_json) for event in _review_events(db_session, identity_seed, task_id)
    )
    assert "Please confirm the synthetic supporting reference." not in audit_text
    assert "Confirmed against the synthetic support document." not in audit_text


def test_rejection_is_terminal_and_authorized_auditor_is_read_only(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
        filename="synthetic-rejected.pdf",
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    task_id = client.post(review_url, headers=_auth_headers(identity_seed), json={}).json()["id"]
    empty_rejection = client.post(
        f"{review_url}/{task_id}/reject",
        headers=_auth_headers(identity_seed),
        json={"reason": ""},
    )
    assert empty_rejection.status_code == 422
    rejected = client.post(
        f"{review_url}/{task_id}/reject",
        headers=_auth_headers(identity_seed),
        json={"reason": "Synthetic evidence is insufficient."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["task"]["status"] == "rejected"
    assert rejected.json()["outcome"]["outcome_type"] == "rejected"

    repository = IdentityRepository(db_session)
    repository.grant_client_access(
        membership_id=identity_seed.auditor_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
    )
    db_session.commit()
    auditor_headers = _auth_headers(
        identity_seed,
        subject=identity_seed.auditor.external_subject,
    )
    auditor_task = client.get(f"{review_url}/{task_id}", headers=auditor_headers)
    auditor_history = client.get(
        f"{review_url}/{task_id}/history",
        headers=auditor_headers,
    )
    auditor_comment = client.post(
        f"{review_url}/{task_id}/comments",
        headers=auditor_headers,
        json={"body": "Auditor must remain read-only."},
    )
    assert auditor_task.status_code == 200
    assert auditor_history.status_code == 200
    assert auditor_history.json()["outcome"]["outcome_type"] == "rejected"
    assert auditor_comment.status_code == 403


def test_review_creation_enforces_rbac_client_isolation_and_owner_scope(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
        filename="synthetic-rbac.pdf",
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    for subject in (
        identity_seed.admin.external_subject,
        identity_seed.auditor.external_subject,
        identity_seed.submitter.external_subject,
    ):
        denied = client.post(
            review_url,
            headers=_auth_headers(identity_seed, subject=subject),
            json={},
        )
        assert denied.status_code == 403

    cross_client = client.post(
        _review_url(
            identity_seed.client_b.id,
            document_id,
            extraction_run_id,
            decision_run_id,
        ),
        headers=_auth_headers(identity_seed),
        json={},
    )
    assert cross_client.status_code == 403

    repository = IdentityRepository(db_session)
    other = repository.add_user(external_subject="dev-phase5-other-accountant")
    db_session.flush()
    membership = repository.add_membership(
        user_id=other.id,
        firm_id=identity_seed.firm_a.id,
        role=Role.ACCOUNTANT.value,
    )
    db_session.flush()
    repository.grant_client_access(
        membership_id=membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_b.id,
    )
    db_session.commit()
    invalid_owner = client.post(
        review_url,
        headers=_auth_headers(identity_seed),
        json={"owner_membership_id": str(membership.id)},
    )
    assert invalid_owner.status_code == 422
    assert invalid_owner.json()["error"]["code"] == "invalid_review_owner"


def _create_decision(
    client: TestClient,
    identity_seed: IdentitySeed,
    *,
    filename: str = "synthetic-phase5.pdf",
) -> tuple[UUID, UUID, UUID, dict[str, object]]:
    document_id = _upload_document(client, identity_seed, filename=filename)
    extraction = _start_extraction(client, identity_seed, document_id=document_id)
    assert extraction.status_code == 201
    extraction_payload = extraction.json()
    extraction_run_id = UUID(extraction_payload["id"])
    decision = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
    )
    assert decision.status_code == 201
    return document_id, extraction_run_id, UUID(decision.json()["id"]), extraction_payload


def _add_senior(
    db_session: Session,
    identity_seed: IdentitySeed,
    *,
    subject: str,
):
    repository = IdentityRepository(db_session)
    senior = repository.add_user(external_subject=subject)
    db_session.flush()
    membership = repository.add_membership(
        user_id=senior.id,
        firm_id=identity_seed.firm_a.id,
        role=Role.SENIOR_REVIEWER.value,
    )
    db_session.flush()
    repository.grant_client_access(
        membership_id=membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
    )
    db_session.commit()
    return senior, membership


def _correct_field(
    client: TestClient,
    identity_seed: IdentitySeed,
    *,
    document_id: UUID,
    extraction_run_id: UUID,
    field_id: UUID,
    normalized_value: str,
    request_id: str,
):
    return client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/documents/{document_id}/extractions/"
        f"{extraction_run_id}/fields/{field_id}/corrections",
        headers=_auth_headers(identity_seed, request_id=request_id),
        json={
            "corrected_raw_value": f"RM {normalized_value}",
            "corrected_normalized_value": normalized_value,
            "corrected_value_type": "decimal",
            "reason": "Synthetic Phase 5 correction.",
        },
    )


def _review_url(
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
) -> str:
    base_url = _decision_url(client_id, document_id, extraction_run_id)
    return f"{base_url}/{decision_run_id}/review-tasks"


def _review_events(
    db_session: Session,
    identity_seed: IdentitySeed,
    task_id: str,
):
    return [
        event
        for event in AuditRepository(db_session).list_for_firm(firm_id=identity_seed.firm_a.id)
        if event.target_id == task_id
    ]
