from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import IdentitySeed


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
) -> dict[str, object]:
    return {
        "provider_batch_reference": batch_reference,
        "account_reference": "synthetic-clearing-account",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "transactions": [
            {
                "source_transaction_id": source_transaction_id,
                "booking_date": "2026-08-15",
                "direction": "debit",
                "amount": amount,
                "currency": "MYR",
                "description": "Synthetic supplier settlement",
                "reference": "SYN-INV-001",
                "counterparty_name": "Synthetic Supplier",
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
