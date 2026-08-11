# Development Guide

## Status

**Current status: Phase 1 — Core Infrastructure (review branch)**

Phase 1 is infrastructure only. It does not implement document upload, OCR, AI recommendations, accounting automation, SQL Account, MyInvois, or production deployment.

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the package and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Start local PostgreSQL:

```bash
docker compose up -d postgres
```

Apply migrations:

```bash
alembic upgrade head
```

Run the API:

```bash
uvicorn ledgerpilot.api.app:create_app --factory --reload
```

Stop local PostgreSQL:

```bash
docker compose down
```

## Health Endpoints

```bash
curl http://127.0.0.1:8000/api/v1/health/live
curl http://127.0.0.1:8000/api/v1/health/ready
```

Readiness checks database connectivity and returns a safe structured failure if the database is unavailable.

## Development Authentication

Development authentication exists only to support local development and automated testing. It is not a production authentication mechanism.

Enable it only in `development` or `test`:

```bash
export LEDGERPILOT_ENV=development
export LEDGERPILOT_AUTH_MODE=development
export LEDGERPILOT_DEV_AUTH_ENABLED=true
```

Development auth uses:

```text
X-LedgerPilot-Dev-Subject
X-LedgerPilot-Firm
```

The request may identify only a synthetic development subject and firm. Roles, permissions, and client access are loaded from persisted users, firm memberships, and client-access records. They are not trusted from request headers.

Production refuses development auth through settings validation. A future production identity provider or secure authentication implementation must replace it before production use.

## Verification

Run:

```bash
python --version
python -m pip --version
python -m pytest
python -m pytest --cov=ledgerpilot --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
```

With local PostgreSQL running:

```bash
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

## Public Repository Rules

Use synthetic data only. Do not commit real client data, credentials, private keys, `.env` files, PostgreSQL volumes, generated databases, or test output containing secrets.
