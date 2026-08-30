from __future__ import annotations

from ledgerpilot.api.vercel import app


def test_vercel_entrypoint_exposes_existing_api_routes() -> None:
    route_paths = {route.path for route in app.routes}

    assert "/api/v1/health/live" in route_paths
    assert "/api/v1/health/ready" in route_paths
    assert "/api/v1/context" in route_paths
    assert any(path.endswith("/bank-reconciliation/worklist") for path in route_paths)
