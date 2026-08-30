from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import IdentitySeed
from tests.integration.test_reconciliation_review_api import (
    _approved_candidate,
    _reviews_url,
)


def test_match_generation_is_frozen_after_human_review_starts(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    headers, transaction_id, match_run_id, _ = _approved_candidate(
        client,
        identity_seed,
        batch_reference="synthetic-review-freeze-batch",
        source_transaction_id="synthetic-review-freeze-tx",
    )
    review = client.post(
        _reviews_url(identity_seed, transaction_id),
        headers=headers,
        json={"match_run_id": match_run_id},
    )
    assert review.status_code == 201

    regenerated = client.post(
        f"/api/v1/clients/{identity_seed.client_a.id}/bank-reconciliation/transactions/"
        f"{transaction_id}/match-runs",
        headers=headers,
        json={},
    )

    assert regenerated.status_code == 409
    assert regenerated.json()["error"]["code"] == "reconciliation_review_started"
