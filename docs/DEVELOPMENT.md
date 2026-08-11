# Development Guide

## Status

**Current status: Phase 2 — Secure Document Intake (review branch)**

Phase 2 implements secure document intake for local development and automated tests. It does not implement OCR, extraction, AI recommendations, accounting automation, review workflows, SQL Account, MyInvois, production authentication, production object storage, production malware scanning, or production deployment.

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

## Local Document Intake Configuration

Phase 2 local document intake uses development-only storage and scanner implementations:

```bash
export LEDGERPILOT_DOCUMENT_STORAGE_BACKEND=local
export LEDGERPILOT_DOCUMENT_STORAGE_ROOT=local_storage
export LEDGERPILOT_MALWARE_SCANNER_MODE=development
export LEDGERPILOT_DOCUMENT_MAX_BYTES=10485760
```

The local storage provider keeps files under:

```text
local_storage/
├── staging/
├── accepted/
└── quarantine/
```

`local_storage/` is ignored by Git and must not be committed. The development scanner is deterministic and synthetic; it is not real malware protection and production refuses it through settings validation.

The implemented Phase 2 endpoints are:

```text
POST /api/v1/clients/{client_id}/documents
GET /api/v1/clients/{client_id}/documents/{document_id}
```

Supported formats are PDF, JPEG, and PNG only. There is no raw document download endpoint in Phase 2.

Manual API testing requires synthetic persisted identity, firm, membership, client, and client-access records. The application does not seed users or clients automatically and must not create synthetic users during production startup.

Example upload shape for a synthetic local file:

```bash
curl -X POST \
  -H "X-LedgerPilot-Dev-Subject: dev-accountant" \
  -H "X-LedgerPilot-Firm: <synthetic-firm-id>" \
  -F "file=@synthetic.pdf;type=application/pdf" \
  http://127.0.0.1:8000/api/v1/clients/<synthetic-client-id>/documents
```

Use only synthetic files. Do not upload or commit real invoices, receipts, statements, personal data, taxpayer identifiers, bank details, or credentials.

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
alembic downgrade 0001_phase_1
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

## Public Repository Rules

Use synthetic data only. Do not commit real client data, credentials, private keys, `.env` files, PostgreSQL volumes, generated databases, or test output containing secrets.
