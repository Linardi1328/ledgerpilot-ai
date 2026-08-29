from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ledgerpilot.persistence.repositories.identity import IdentityRepository
from tests.conftest import IdentitySeed
from tests.integration.test_review_task_api import _create_decision, _review_url


def _headers(subject: str, firm_id: object) -> dict[str, str]:
    return {
        "X-LedgerPilot-Dev-Subject": subject,
        "X-LedgerPilot-Firm": str(firm_id),
    }


def _payload(
    *,
    batch_reference: str = "synthetic-batch-api-1",
    source_transaction_id: str = "synthetic-tx-api-1",
    amount: object = "125.50",
    booking_date: str = "2026-08-15",
    counterparty_name: str = "Synthetic Supplier",
) -> dict[str, object]:
    return {
        "provider_batch_reference": batch_reference,
        "account_reference": "synthetic-clearing-account",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "transactions": [
            {
                "source_transaction_id": source_transaction_id,
                "booking_date": booking_date,
                "direction": "debit",
                "amount": amount,
                "currency": "MYR",
                "description": "Synthetic supplier settlement",
                "reference": "SYN-INV-001",
                "counterparty_name": counterparty_name,
            }
        ],
    }


def test_accountant_can_create_and_read_synthetic_bank_import(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    path = f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic"

    created = client.post(path, headers=headers, json=_payload())

    assert created.status_code == 201
    payload = created.json()
    assert payload["created"] is True
    assert payload["batch"]["provider_name"] == "synthetic_bank_feed"
    assert payload["batch"]["provider_version"] == "1.0"
    assert len(payload["transactions"]) == 1
    transaction = payload["transactions"][0]
    assert Decimal(transaction["amount"]) == Decimal("125.50")
    assert transaction["currency"] == "MYR"

    batch_id = payload["batch"]["id"]
    transaction_id = transaction["id"]

    listed = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports",
        headers=headers,
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [batch_id]

    batch = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/{batch_id}",
        headers=headers,
    )
    assert batch.status_code == 200
    assert batch.json()["id"] == batch_id

    transactions = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/{batch_id}/transactions",
        headers=headers,
    )
    assert transactions.status_code == 200
    assert [item["id"] for item in transactions.json()] == [transaction_id]

    transaction_response = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/{transaction_id}",
        headers=headers,
    )
    assert transaction_response.status_code == 200
    assert transaction_response.json()["source_transaction_id"] == "synthetic-tx-api-1"

    runs = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/{transaction_id}/match-runs",
        headers=headers,
    )
    assert runs.status_code == 200
    assert runs.json() == []


def test_exact_replay_is_idempotent(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    path = f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic"

    first = client.post(path, headers=headers, json=_payload())
    second = client.post(path, headers=headers, json=_payload())

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["batch"]["id"] == first.json()["batch"]["id"]
    assert second.json()["transactions"][0]["id"] == first.json()["transactions"][0]["id"]


def test_reusing_batch_reference_with_different_payload_is_rejected(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    path = f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic"

    first = client.post(path, headers=headers, json=_payload())
    conflict = client.post(
        path,
        headers=headers,
        json=_payload(amount="126.00"),
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "bank_import_batch_conflict"


def test_cross_import_duplicate_source_transaction_is_rejected(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    path = f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic"

    first = client.post(path, headers=headers, json=_payload())
    duplicate = client.post(
        path,
        headers=headers,
        json=_payload(batch_reference="synthetic-batch-api-2"),
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "bank_transaction_already_imported"


def test_client_submitter_cannot_import_or_view_bank_transactions(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.submitter.external_subject,
        identity_seed.firm_a.id,
    )
    base = f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation"

    imported = client.post(
        f"{base}/imports/synthetic",
        headers=headers,
        json=_payload(),
    )
    listed = client.get(f"{base}/imports", headers=headers)

    assert imported.status_code == 403
    assert listed.status_code == 403


def test_accountant_cannot_access_unassigned_client_bank_data(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )

    response = client.get(
        f"/api/v1/clients/{identity_seed.client_b.id}/bank-reconciliation/imports",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_bank_import_rejects_json_number_money_and_excess_precision(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    path = f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic"

    number_amount = client.post(path, headers=headers, json=_payload(amount=125.5))
    excessive_precision = client.post(
        path,
        headers=headers,
        json=_payload(amount="125.00001"),
    )

    assert number_amount.status_code == 422
    assert excessive_precision.status_code == 422


def test_match_generation_uses_only_server_projected_approved_outcome(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(identity_seed.accountant.external_subject, identity_seed.firm_a.id)
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(client, identity_seed)
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    task = client.post(review_url, headers=headers, json={}).json()
    approved = client.post(f"{review_url}/{task['id']}/approve", headers=headers, json={})
    assert approved.status_code == 200
    outcome_id = approved.json()["outcome"]["id"]

    import_response = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic",
        headers=headers,
        json=_payload(
            batch_reference="synthetic-match-batch-1",
            source_transaction_id="synthetic-match-tx-1",
            amount="100.00",
            booking_date="2026-08-11",
            counterparty_name="Synthetic Office Supplies Sdn. Bhd.",
        ),
    )
    assert import_response.status_code == 201
    transaction_id = import_response.json()["transactions"][0]["id"]

    match = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
        f"{transaction_id}/match-runs",
        headers=headers,
        json={},
    )

    assert match.status_code == 201
    payload = match.json()
    assert payload["run"]["status"] == "candidates_available"
    assert len(payload["candidates"]) == 1
    candidate = payload["candidates"][0]
    assert candidate["review_outcome_id"] == outcome_id
    assert candidate["document_id"] == str(document_id)
    assert Decimal(candidate["score"]) == Decimal("1.0000")
    assert Decimal(candidate["target_amount"]) == Decimal("100.00")
    assert candidate["target_currency"] == "MYR"
    assert candidate["target_direction"] == "debit"
    assert candidate["target_reference"] == "SYN-INV-001"


def test_rejected_review_outcome_is_not_a_reconciliation_target(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers = _headers(identity_seed.accountant.external_subject, identity_seed.firm_a.id)
    document_id, extraction_run_id, decision_run_id, _ = _create_decision(
        client,
        identity_seed,
        filename="synthetic-reconciliation-rejected.pdf",
    )
    review_url = _review_url(
        identity_seed.client_a.id,
        document_id,
        extraction_run_id,
        decision_run_id,
    )
    task = client.post(review_url, headers=headers, json={}).json()
    rejected = client.post(
        f"{review_url}/{task['id']}/reject",
        headers=headers,
        json={"reason": "Synthetic rejected reconciliation target."},
    )
    assert rejected.status_code == 200

    import_response = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic",
        headers=headers,
        json=_payload(
            batch_reference="synthetic-match-batch-rejected",
            source_transaction_id="synthetic-match-tx-rejected",
            amount="100.00",
            booking_date="2026-08-11",
        ),
    )
    transaction_id = import_response.json()["transactions"][0]["id"]

    match = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
        f"{transaction_id}/match-runs",
        headers=headers,
        json={},
    )

    assert match.status_code == 201
    assert match.json()["run"]["status"] == "unmatched"
    assert match.json()["candidates"] == []


def test_auditor_can_read_but_cannot_generate_reconciliation_matches(
    client: TestClient,
    db_session: Session,
    identity_seed: IdentitySeed,
) -> None:
    accountant_headers = _headers(
        identity_seed.accountant.external_subject,
        identity_seed.firm_a.id,
    )
    imported = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/imports/synthetic",
        headers=accountant_headers,
        json=_payload(
            batch_reference="synthetic-auditor-batch",
            source_transaction_id="synthetic-auditor-tx",
        ),
    )
    transaction_id = imported.json()["transactions"][0]["id"]

    IdentityRepository(db_session).grant_client_access(
        membership_id=identity_seed.auditor_membership.id,
        firm_id=identity_seed.firm_a.id,
        client_id=identity_seed.client_a.id,
    )
    db_session.commit()
    auditor_headers = _headers(identity_seed.auditor.external_subject, identity_seed.firm_a.id)

    read = client.get(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
        f"{transaction_id}/match-runs",
        headers=auditor_headers,
    )
    generate = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
        f"{transaction_id}/match-runs",
        headers=auditor_headers,
        json={},
    )

    assert read.status_code == 200
    assert generate.status_code == 403
