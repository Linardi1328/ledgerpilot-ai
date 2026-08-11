from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from ledgerpilot.api.app import create_app
from ledgerpilot.api.middleware import REQUEST_ID_HEADER, is_valid_request_id
from ledgerpilot.core.config import AuthMode, Environment, Settings
from tests.conftest import IdentitySeed


def test_app_creation(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200


def test_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.json() == {"status": "ok"}


def test_readiness(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


def test_safe_readiness_failure() -> None:
    settings = Settings(
        env=Environment.TEST,
        database_url="sqlite+pysqlite:////not/a/real/path/ledgerpilot.db",
        auth_mode=AuthMode.DISABLED,
        dev_auth_enabled=False,
    )
    app = create_app(settings=settings)
    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["checks"] == {"database": "unavailable"}
    assert "ledgerpilot.db" not in response.text
    assert "Traceback" not in response.text


def test_request_id_generation(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    request_id = response.headers[REQUEST_ID_HEADER]
    assert is_valid_request_id(request_id)


def test_valid_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/api/v1/health/live", headers={REQUEST_ID_HEADER: "req-123"})
    assert response.headers[REQUEST_ID_HEADER] == "req-123"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/v1/health/live", headers={REQUEST_ID_HEADER: "x" * 200})
    assert response.headers[REQUEST_ID_HEADER] != "x" * 200
    assert is_valid_request_id(response.headers[REQUEST_ID_HEADER])


def test_structured_not_found_error(client: TestClient) -> None:
    response = client.get("/api/v1/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_protected_context_denies_unauthenticated_access(client: TestClient) -> None:
    response = client.get("/api/v1/context")
    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "unauthenticated",
        "message": "Authentication required.",
        "request_id": response.headers[REQUEST_ID_HEADER],
    }


def test_development_auth_disabled_by_default(
    session_factory: sessionmaker,
    identity_seed: IdentitySeed,
) -> None:
    settings = Settings(
        env=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        auth_mode=AuthMode.DISABLED,
        dev_auth_enabled=False,
    )
    app = create_app(settings=settings, session_factory=session_factory)
    with TestClient(app) as test_client:
        response = test_client.get(
            "/api/v1/context",
            headers={
                "X-LedgerPilot-Dev-Subject": identity_seed.accountant.external_subject,
                "X-LedgerPilot-Firm": str(identity_seed.firm_a.id),
            },
        )
    assert response.status_code == 401


def test_development_auth_loads_role_and_client_access_from_persistence(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    response = client.get(
        "/api/v1/context",
        headers={
            "X-LedgerPilot-Dev-Subject": identity_seed.accountant.external_subject,
            "X-LedgerPilot-Firm": str(identity_seed.firm_a.id),
            "X-LedgerPilot-Role": "senior_reviewer",
            "X-LedgerPilot-Client-Ids": str(identity_seed.client_b.id),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "accountant"
    assert payload["authorized_client_ids"] == [str(identity_seed.client_a.id)]


def test_user_without_membership_cannot_enter_firm(
    client: TestClient,
    identity_seed: IdentitySeed,
) -> None:
    response = client.get(
        "/api/v1/context",
        headers={
            "X-LedgerPilot-Dev-Subject": identity_seed.outsider.external_subject,
            "X-LedgerPilot-Firm": str(identity_seed.firm_a.id),
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
