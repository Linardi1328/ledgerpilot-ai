from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ledgerpilot.audit.types import AuditEventType
from ledgerpilot.persistence.repositories.audit import AuditRepository
from ledgerpilot.persistence.repositories.identity import IdentityRepository
from tests.conftest import IdentitySeed
from tests.integration.test_reconciliation_api import _headers, _payload
from tests.integration.test_review_task_api import _create_decision, _review_url


def test_human_can_select_candidate_and_approve_terminal_reconciliation(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    headers, transaction_id, match_run_id, review_outcome_id = _approved_candidate(
        client,
        identity_seed,
        batch_reference="synthetic-human-review-batch-1",
        source_transaction_id="synthetic-human-review-tx-1",
    )
    base = _reviews_url(identity_seed, transaction_id)

    created = client.post(
        base,
        headers=headers,
        json={"match_run_id": match_run_id},
    )
    assert created.status_code == 201
    review = created.json()
    assert review["status"] == "open"
    assert review["selected_review_outcome_id"] is None

    missing_candidate = client.post(
        f"{base}/{review['id']}/approve",
        headers=headers,
        json={},
    )
    assert missing_candidate.status_code == 409
    assert missing_candidate.json()["error"]["code"] == "reconciliation_candidate_required"

    selected = client.post(
        f"{base}/{review['id']}/candidate-selection",
        headers=headers,
        json={"review_outcome_id": review_outcome_id},
    )
    assert selected.status_code == 200
    assert selected.json()["selected_review_outcome_id"] == review_outcome_id

    note = "Synthetic human reconciliation approval."
    approved = client.post(
        f"{base}/{review['id']}/approve",
        headers=headers,
        json={"note": note},
    )
    assert approved.status_code == 200
    approved_payload = approved.json()
    assert approved_payload["review"]["status"] == "matched"
    assert approved_payload["outcome"]["outcome_type"] == "matched"
    assert approved_payload["outcome"]["matched_review_outcome_id"] == review_outcome_id

    history = client.get(
        f"{base}/{review['id']}/history",
        headers=headers,
    )
    assert history.status_code == 200
    history_payload = history.json()
    assert [item["action_type"] for item in history_payload["actions"]] == [
        "candidate_selected",
        "approved_match",
    ]
    assert history_payload["outcome"]["outcome_type"] == "matched"

    terminal_change = client.post(
        f"{base}/{review['id']}/mark-unmatched",
        headers=headers,
        json={"reason": "Synthetic late unmatched attempt."},
    )
    assert terminal_change.status_code == 409
    assert terminal_change.json()["error"]["code"] == "reconciliation_review_terminal"

    events = [
        event
        for event in AuditRepository(db_session).list_for_firm(
            firm_id=identity_seed.firm_a.id
        )
        if event.target_id == review["id"]
    ]
    assert [event.event_type for event in events] == [
        AuditEventType.RECONCILIATION_REVIEW_CREATED.value,
        AuditEventType.RECONCILIATION_CANDIDATE_SELECTED.value,
        AuditEventType.RECONCILIATION_APPROVED.value,
    ]
    assert note not in " ".join(str(event.metadata_json) for event in events)


def test_dispute_blocks_match_approval_until_reopened_and_can_end_unmatched(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers, transaction_id, match_run_id, review_outcome_id = _approved_candidate(
        client,
        identity_seed,
        batch_reference="synthetic-human-review-batch-2",
        source_transaction_id="synthetic-human-review-tx-2",
    )
    base = _reviews_url(identity_seed, transaction_id)
    review = client.post(
        base,
        headers=headers,
        json={"match_run_id": match_run_id},
    ).json()

    selected = client.post(
        f"{base}/{review['id']}/candidate-selection",
        headers=headers,
        json={"review_outcome_id": review_outcome_id},
    )
    assert selected.status_code == 200

    disputed = client.post(
        f"{base}/{review['id']}/dispute",
        headers=headers,
        json={"reason": "Synthetic evidence needs another check."},
    )
    assert disputed.status_code == 200
    assert disputed.json()["status"] == "disputed"

    blocked_approval = client.post(
        f"{base}/{review['id']}/approve",
        headers=headers,
        json={},
    )
    assert blocked_approval.status_code == 409
    assert blocked_approval.json()["error"]["code"] == "reconciliation_disputed"

    reopened = client.post(
        f"{base}/{review['id']}/reopen",
        headers=headers,
        json={"reason": "Synthetic dispute resolved for final review."},
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"

    disputed_again = client.post(
        f"{base}/{review['id']}/dispute",
        headers=headers,
        json={"reason": "Synthetic reviewer elects unmatched resolution."},
    )
    assert disputed_again.status_code == 200

    unmatched = client.post(
        f"{base}/{review['id']}/mark-unmatched",
        headers=headers,
        json={"reason": "Synthetic transaction should remain unmatched."},
    )
    assert unmatched.status_code == 200
    assert unmatched.json()["review"]["status"] == "unmatched"
    assert unmatched.json()["outcome"]["outcome_type"] == "unmatched"
    assert unmatched.json()["outcome"]["matched_review_outcome_id"] is None

    history = client.get(f"{base}/{review['id']}/history", headers=headers)
    assert history.status_code == 200
    assert [item["action_type"] for item in history.json()["actions"]] == [
        "candidate_selected",
        "disputed",
        "reopened",
        "disputed",
        "marked_unmatched",
    ]


def test_auditor_can_read_reconciliation_history_but_cannot_mutate(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    headers, transaction_id, match_run_id, _ = _approved_candidate(
        client,
        identity_seed,
        batch_reference="synthetic-human-review-batch-3",
        source_transaction_id="synthetic-human-review-tx-3",
    )
    base = _reviews_url(identity_seed, transaction_id)
    review = client.post(
        base,
        headers=headers,
        json={"match_run_id": match_run_id},
    ).json()

    IdentityRepository(db_session).grant_client_access(
        membership_id=identity_seed.auditor_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
    )
    db_session.commit()
    auditor_headers = _headers(
        identity_seed.auditor.external_subject,
        identity_seed.firm_a.id,
    )

    fetched = client.get(
        f"{base}/{review['id']}",
        headers=auditor_headers,
    )
    history = client.get(
        f"{base}/{review['id']}/history",
        headers=auditor_headers,
    )
    disputed = client.post(
        f"{base}/{review['id']}/dispute",
        headers=auditor_headers,
        json={"reason": "Auditor must remain read-only."},
    )
    approved = client.post(
        f"{base}/{review['id']}/approve",
        headers=auditor_headers,
        json={},
    )

    assert fetched.status_code == 200
    assert history.status_code == 200
    assert disputed.status_code == 403
    assert approved.status_code == 403


def test_same_approved_accounting_outcome_cannot_match_two_bank_transactions(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
        filename="synthetic-reconciliation-duplicate-target.pdf",
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    task = client.post(review_url, headers=headers, json={}).json()
    approved = client.post(
        f"{review_url}/{task['id']}/approve",
        headers=headers,
        json={},
    )
    assert approved.status_code == 200
    review_outcome_id = approved.json()["outcome"]["id"]

    import_payload = _payload(
        batch_reference="synthetic-human-review-duplicate-batch",
        source_transaction_id="synthetic-human-review-duplicate-tx-1",
        amount="100.00",
        booking_date="2026-08-11",
        counterparty_name="Synthetic Office Supplies Sdn. Bhd.",
    )
    first_transaction = dict(import_payload["transactions"][0])
    second_transaction = dict(first_transaction)
    second_transaction["source_transaction_id"] = "synthetic-human-review-duplicate-tx-2"
    import_payload["transactions"] = [first_transaction, second_transaction]

    imported = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic",
        headers=headers,
        json=import_payload,
    )
    assert imported.status_code == 201
    transaction_ids = [item["id"] for item in imported.json()["transactions"]]
    assert len(transaction_ids) == 2

    reviews: list[tuple[str, str]] = []
    for transaction_id in transaction_ids:
        match = client.post(
            f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
            f"{transaction_id}/match-runs",
            headers=headers,
            json={},
        )
        assert match.status_code == 201
        assert match.json()["candidates"][0]["review_outcome_id"] == review_outcome_id
        match_run_id = match.json()["run"]["id"]
        base = _reviews_url(identity_seed, transaction_id)
        review = client.post(
            base,
            headers=headers,
            json={"match_run_id": match_run_id},
        )
        assert review.status_code == 201
        review_id = review.json()["id"]
        selected = client.post(
            f"{base}/{review_id}/candidate-selection",
            headers=headers,
            json={"review_outcome_id": review_outcome_id},
        )
        assert selected.status_code == 200
        reviews.append((base, review_id))

    first_approval = client.post(
        f"{reviews[0][0]}/{reviews[0][1]}/approve",
        headers=headers,
        json={},
    )
    second_approval = client.post(
        f"{reviews[1][0]}/{reviews[1][1]}/approve",
        headers=headers,
        json={},
    )

    assert first_approval.status_code == 200
    assert second_approval.status_code == 409
    assert second_approval.json()["error"]["code"] == "reconciliation_target_already_matched"


def _approved_candidate(
    client: TestClient,
    identity_seed: IdentitySeed,
    *,
    batch_reference: str,
    source_transaction_id: str,
) -> tuple[dict[str, str], str, str, str]:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
        filename=f"{source_transaction_id}.pdf",
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    task = client.post(review_url, headers=headers, json={})
    assert task.status_code == 201
    approved = client.post(
        f"{review_url}/{task.json()['id']}/approve",
        headers=headers,
        json={},
    )
    assert approved.status_code == 200
    review_outcome_id = approved.json()["outcome"]["id"]

    imported = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic",
        headers=headers,
        json=_payload(
            batch_reference=batch_reference,
            source_transaction_id=source_transaction_id,
            amount="100.00",
            booking_date="2026-08-11",
            counterparty_name="Synthetic Office Supplies Sdn. Bhd.",
        ),
    )
    assert imported.status_code == 201
    transaction_id = imported.json()["transactions"][0]["id"]

    matched = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
        f"{transaction_id}/match-runs",
        headers=headers,
        json={},
    )
    assert matched.status_code == 201
    assert matched.json()["run"]["status"] == "candidates_available"
    assert matched.json()["candidates"][0]["review_outcome_id"] == review_outcome_id

    return headers, transaction_id, matched.json()["run"]["id"], review_outcome_id


def _reviews_url(identity_seed: IdentitySeed, transaction_id: str) -> str:
    return (
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
        f"{transaction_id}/reviews"
    )
