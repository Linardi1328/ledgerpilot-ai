from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ledgerpilot.persistence.repositories.identity import IdentityRepository
from tests.conftest import IdentitySeed
from tests.integration.test_reconciliation_api import _headers, _payload
from tests.integration.test_review_task_api import _create_decision, _review_url


def test_worklist_projects_server_authoritative_reconciliation_states(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    review_outcome_id = _approved_review_outcome(client, identity_seed, headers)

    import_payload = _payload(
        batch_reference="synthetic-worklist-batch",
        source_transaction_id="synthetic-worklist-template",
        amount="100.00",
        booking_date="2026-08-11",
        counterparty_name="Synthetic Office Supplies Sdn. Bhd.",
    )
    template = dict(import_payload["transactions"][0])
    transaction_specs = [
        ("not-evaluated", "100.00"),
        ("unmatched", "999.00"),
        ("candidates", "100.00"),
        ("in-review", "100.00"),
        ("disputed", "100.00"),
        ("matched", "100.00"),
        ("resolved-unmatched", "100.00"),
    ]
    transactions: list[dict[str, object]] = []
    for suffix, amount in transaction_specs:
        transaction = deepcopy(template)
        transaction["source_transaction_id"] = f"synthetic-worklist-{suffix}"
        transaction["amount"] = amount
        transactions.append(transaction)
    import_payload["transactions"] = transactions

    imported = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic",
        headers=headers,
        json=import_payload,
    )
    assert imported.status_code == 201
    transaction_ids = {
        item["source_transaction_id"]: item["id"] for item in imported.json()["transactions"]
    }

    match_runs: dict[str, str] = {}
    for source_id, transaction_id in transaction_ids.items():
        if source_id.endswith("not-evaluated"):
            continue
        matched = client.post(
            f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
            f"{transaction_id}/match-runs",
            headers=headers,
            json={},
        )
        assert matched.status_code == 201
        match_runs[source_id] = matched.json()["run"]["id"]
        if source_id.endswith("unmatched") and not source_id.endswith("resolved-unmatched"):
            assert matched.json()["run"]["status"] == "unmatched"
        else:
            assert matched.json()["run"]["status"] == "candidates_available"
            assert matched.json()["candidates"][0]["review_outcome_id"] == review_outcome_id

    in_review = _create_reconciliation_review(
        client,
        identity_seed,
        headers,
        transaction_ids["synthetic-worklist-in-review"],
        match_runs["synthetic-worklist-in-review"],
    )
    assert in_review["status"] == "open"

    disputed = _create_reconciliation_review(
        client,
        identity_seed,
        headers,
        transaction_ids["synthetic-worklist-disputed"],
        match_runs["synthetic-worklist-disputed"],
    )
    disputed_response = client.post(
        f"{_reviews_url(identity_seed, transaction_ids['synthetic-worklist-disputed'])}/"
        f"{disputed['id']}/dispute",
        headers=headers,
        json={"reason": "Synthetic worklist dispute."},
    )
    assert disputed_response.status_code == 200

    matched_review = _create_reconciliation_review(
        client,
        identity_seed,
        headers,
        transaction_ids["synthetic-worklist-matched"],
        match_runs["synthetic-worklist-matched"],
    )
    matched_base = _reviews_url(identity_seed, transaction_ids["synthetic-worklist-matched"])
    selected = client.post(
        f"{matched_base}/{matched_review['id']}/candidate-selection",
        headers=headers,
        json={"review_outcome_id": review_outcome_id},
    )
    assert selected.status_code == 200
    approved = client.post(
        f"{matched_base}/{matched_review['id']}/approve",
        headers=headers,
        json={},
    )
    assert approved.status_code == 200

    unmatched_review = _create_reconciliation_review(
        client,
        identity_seed,
        headers,
        transaction_ids["synthetic-worklist-resolved-unmatched"],
        match_runs["synthetic-worklist-resolved-unmatched"],
    )
    unmatched_base = _reviews_url(
        identity_seed,
        transaction_ids["synthetic-worklist-resolved-unmatched"],
    )
    closed_unmatched = client.post(
        f"{unmatched_base}/{unmatched_review['id']}/mark-unmatched",
        headers=headers,
        json={"reason": "Synthetic worklist unmatched resolution."},
    )
    assert closed_unmatched.status_code == 200

    worklist = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/worklist",
        headers=headers,
    )
    assert worklist.status_code == 200
    states = {
        item["transaction"]["source_transaction_id"]: item["workflow_state"]
        for item in worklist.json()
    }
    assert states == {
        "synthetic-worklist-not-evaluated": "not_evaluated",
        "synthetic-worklist-unmatched": "unmatched",
        "synthetic-worklist-candidates": "candidates_available",
        "synthetic-worklist-in-review": "in_review",
        "synthetic-worklist-disputed": "disputed",
        "synthetic-worklist-matched": "matched",
        "synthetic-worklist-resolved-unmatched": "resolved_unmatched",
    }

    disputed_only = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/worklist",
        headers=headers,
        params={"state": "disputed"},
    )
    assert disputed_only.status_code == 200
    assert [item["transaction"]["source_transaction_id"] for item in disputed_only.json()] == [
        "synthetic-worklist-disputed"
    ]


def test_worklist_is_auditor_readable_and_submitter_forbidden(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    IdentityRepository(db_session).grant_client_access(
        membership_id=identity_seed.auditor_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
    )
    db_session.commit()
    path = f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/worklist"

    auditor = client.get(
        path,
        headers=_headers(identity_seed.auditor.external_subject, identity_seed.firm_a.id),
    )
    submitter = client.get(
        path,
        headers=_headers(identity_seed.submitter.external_subject, identity_seed.firm_a.id),
    )

    assert auditor.status_code == 200
    assert submitter.status_code == 403


def _approved_review_outcome(
    client: TestClient,
    identity_seed: IdentitySeed,
    headers: dict[str, str],
) -> str:
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
        filename="synthetic-worklist-approved-target.pdf",
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
    return str(approved.json()["outcome"]["id"])


def _create_reconciliation_review(
    client: TestClient,
    identity_seed: IdentitySeed,
    headers: dict[str, str],
    transaction_id: str,
    match_run_id: str,
) -> dict[str, object]:
    created = client.post(
        _reviews_url(identity_seed, transaction_id),
        headers=headers,
        json={"match_run_id": match_run_id},
    )
    assert created.status_code == 201
    return dict(created.json())


def _reviews_url(identity_seed: IdentitySeed, transaction_id: str) -> str:
    return (
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
        f"{transaction_id}/reviews"
    )
