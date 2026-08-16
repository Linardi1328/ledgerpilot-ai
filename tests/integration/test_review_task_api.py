from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ledgerpilot.api.errors import ApiError
from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.identity.authorization import permissions_for_role
from ledgerpilot.identity.principal import Principal
from ledgerpilot.identity.roles import Role
from ledgerpilot.persistence.models.accounting import AccountingDecisionRun
from ledgerpilot.persistence.repositories.audit import AuditRepository
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from ledgerpilot.review.service import ReviewTaskService
from tests.conftest import IdentitySeed
from tests.integration.test_accounting_decision_api import (
    _auth_headers,
    _decision_url,
    _start_decision,
    _start_extraction,
    _upload_document,
)


def test_accountant_creates_scoped_review_task_without_auto_approval(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id, extraction_run_id, decision_run_id = _create_phase4_decision(
        client,
        identity_seed,
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )

    response = client.post(
        review_url,
        headers=_auth_headers(identity_seed, request_id="req-phase5-review-create"),
        json={},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["decision_run_id"] == str(decision_run_id)
    assert payload["document_id"] == str(document_id)
    assert payload["extraction_run_id"] == str(extraction_run_id)
    assert payload["owner_user_id"] == str(identity_seed.accountant.id)
    assert payload["owner_membership_id"] == str(identity_seed.accountant_membership.id)
    assert payload["status"] == "open"
    assert payload["escalation_state"] == "none"
    assert payload["escalated_at"] is None

    decision = db_session.get(AccountingDecisionRun, decision_run_id)
    assert decision is not None
    assert decision.status == "succeeded"

    events = [
        event
        for event in AuditRepository(db_session).list_for_firm(firm_id=identity_seed.firm_a.id)
        if event.target_id == payload["id"]
    ]
    assert [event.event_type for event in events] == [AuditEventType.REVIEW_TASK_CREATED.value]
    assert all("approv" not in event.event_type for event in events)

    list_response = client.get(review_url, headers=_auth_headers(identity_seed))
    get_response = client.get(
        f"{review_url}/{payload['id']}",
        headers=_auth_headers(identity_seed),
    )
    assert list_response.status_code == 200
    assert [task["id"] for task in list_response.json()] == [payload["id"]]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == payload["id"]

    senior, _ = _add_senior_reviewer(db_session, identity_seed, subject="dev-phase5-reader")
    senior_read = client.get(
        f"{review_url}/{payload['id']}",
        headers=_auth_headers(identity_seed, subject=senior.external_subject),
    )
    assert senior_read.status_code == 200

    duplicate = client.post(review_url, headers=_auth_headers(identity_seed), json={})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "review_task_exists"


def test_review_task_api_enforces_rbac_and_client_isolation(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    document_id, extraction_run_id, decision_run_id = _create_phase4_decision(
        client,
        identity_seed,
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
        create_response = client.post(
            review_url,
            headers=_auth_headers(identity_seed, subject=subject),
            json={},
        )
        read_response = client.get(
            review_url,
            headers=_auth_headers(identity_seed, subject=subject),
        )
        assert create_response.status_code == 403
        assert read_response.status_code == 403

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


def test_invalid_review_owner_is_rejected_before_persistence(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id, extraction_run_id, decision_run_id = _create_phase4_decision(
        client,
        identity_seed,
    )
    repository = IdentityRepository(db_session)
    other_accountant = repository.add_user(external_subject="dev-phase5-other-accountant")
    db_session.flush()
    other_membership = repository.add_membership(
        user_id=other_accountant.id,
        firm_id=identity_seed.firm_a.id,
        role=Role.ACCOUNTANT.value,
    )
    db_session.flush()
    repository.grant_client_access(
        membership_id=other_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_b.id,
    )
    db_session.commit()

    response = client.post(
        _review_url(
            identity_seed.client_a.id,
            document_id,
            extraction_run_id,
            decision_run_id,
        ),
        headers=_auth_headers(identity_seed),
        json={"owner_membership_id": str(other_membership.id)},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_review_owner"


def test_senior_escalation_is_deterministic_scoped_and_audited(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    document_id, extraction_run_id, decision_run_id = _create_phase4_decision(
        client,
        identity_seed,
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    create_response = client.post(
        review_url,
        headers=_auth_headers(identity_seed),
        json={},
    )
    assert create_response.status_code == 201
    review_task_id = UUID(create_response.json()["id"])

    senior, senior_membership = _add_senior_reviewer(
        db_session, identity_seed, subject="dev-phase5-senior"
    )

    principal = Principal(
        user_id=identity_seed.accountant.id,
        firm_id=identity_seed.firm_a.id,
        membership_id=identity_seed.accountant_membership.id,
        role=Role.ACCOUNTANT,
        authorized_client_ids=frozenset({identity_seed.client_a.id}),
        permissions=permissions_for_role(Role.ACCOUNTANT),
    )
    service = ReviewTaskService(session=db_session)
    with pytest.raises(ApiError) as invalid_target:
        service.escalate_to_senior(
            principal=principal,
            client_id=identity_seed.client_a.id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
            senior_membership_id=identity_seed.accountant_membership.id,
            request_id="req-phase5-invalid-escalation-owner",
        )
    assert invalid_target.value.status_code == 422
    assert invalid_target.value.code == "invalid_review_owner"

    escalated = service.escalate_to_senior(
        principal=principal,
        client_id=identity_seed.client_a.id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
        senior_membership_id=senior_membership.id,
        request_id="req-phase5-escalate",
    )

    assert escalated.status == "escalated"
    assert escalated.escalation_state == "senior_review"
    assert escalated.owner_user_id == senior.id
    assert escalated.owner_membership_id == senior_membership.id
    assert escalated.escalated_at is not None

    events = [
        event
        for event in AuditRepository(db_session).list_for_firm(firm_id=identity_seed.firm_a.id)
        if event.target_id == str(review_task_id)
    ]
    assert [event.event_type for event in events] == [
        AuditEventType.REVIEW_TASK_CREATED.value,
        AuditEventType.REVIEW_TASK_ESCALATED.value,
    ]
    assert events[-1].metadata_json["senior_owner_membership_id"] == str(senior_membership.id)
    assert events[-1].metadata_json["escalation_state"] == "senior_review"

    with pytest.raises(ApiError) as error:
        service.escalate_to_senior(
            principal=principal,
            client_id=identity_seed.client_a.id,
            document_id=document_id,
            extraction_run_id=extraction_run_id,
            decision_run_id=decision_run_id,
            review_task_id=review_task_id,
            senior_membership_id=senior_membership.id,
            request_id="req-phase5-escalate-again",
        )
    assert error.value.status_code == 409
    assert error.value.code == "review_task_already_escalated"


def _add_senior_reviewer(
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


def _create_phase4_decision(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> tuple[UUID, UUID, UUID]:
    document_id = _upload_document(client, identity_seed)
    extraction = _start_extraction(client, identity_seed, document_id=document_id)
    assert extraction.status_code == 201
    extraction_run_id = UUID(extraction.json()["id"])
    decision = _start_decision(
        client,
        identity_seed,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
    )
    assert decision.status_code == 201
    return document_id, extraction_run_id, UUID(decision.json()["id"])


def _review_url(
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
) -> str:
    return (
        f"{_decision_url(client_id, document_id, extraction_run_id)}/"
        f"{decision_run_id}/review-tasks"
    )
