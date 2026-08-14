# Development Guide

## Status

**Current status: Phase 4 — Accounting Decision Engine Foundation (review branch)**

Phase 4 implements secure document intake, deterministic structured extraction, and a synthetic accounting decision foundation for local development and automated tests. It does not implement production OCR, production accounting/tax policy, approval workflows, SQL Account, MyInvois, production authentication, production object storage, production malware scanning, or production deployment.

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

## Local Document Intake, Extraction, and Accounting Decision Configuration

Phase 2 local document intake uses development-only storage and scanner implementations. Phase 3 adds a development-only extraction provider. Phase 4 adds a synthetic accounting decision policy in application code for local development and tests:

```bash
export LEDGERPILOT_DOCUMENT_STORAGE_BACKEND=local
export LEDGERPILOT_DOCUMENT_STORAGE_ROOT=local_storage
export LEDGERPILOT_MALWARE_SCANNER_MODE=development
export LEDGERPILOT_DOCUMENT_MAX_BYTES=10485760
export LEDGERPILOT_EXTRACTION_PROVIDER=development
export LEDGERPILOT_EXTRACTION_SCHEMA_VERSION=ledgerpilot.extraction.v1
export LEDGERPILOT_EXTRACTION_MAX_FIELDS=500
export LEDGERPILOT_EXTRACTION_MAX_VALUE_CHARS=4000
```

The local storage provider keeps files under:

```text
local_storage/
├── staging/
├── accepted/
└── quarantine/
```

`local_storage/` is ignored by Git and must not be committed. The development scanner is deterministic and synthetic; it is not real malware protection. The development extraction provider is deterministic synthetic test infrastructure; it is not real OCR and is not evidence of OCR accuracy. The Phase 4 accounting policy is synthetic fixture configuration, not professional accounting or tax advice. Production refuses development scanner and extraction providers through settings validation.

The implemented Phase 2 endpoints are:

```text
POST /api/v1/clients/{client_id}/documents
GET /api/v1/clients/{client_id}/documents/{document_id}
```

Supported upload formats are PDF, JPEG, and PNG only. There is no raw document download endpoint through Phase 4.

The implemented Phase 3 endpoints are:

```text
POST /api/v1/clients/{client_id}/documents/{document_id}/extractions
GET /api/v1/clients/{client_id}/documents/{document_id}/extractions
GET /api/v1/clients/{client_id}/documents/{document_id}/extractions/{run_id}
POST /api/v1/clients/{client_id}/documents/{document_id}/extractions/{run_id}/fields/{field_id}/corrections
```

The implemented Phase 4 endpoints are:

```text
POST /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions
GET /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions
GET /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions/{decision_run_id}
```

Only succeeded downstream-ready extraction runs are eligible for accounting decisions. Decision execution requires the `run_accounting_decision` permission.

Phase 4 currently supports purchase-invoice-specific recommendations and proposed journals only when the effective `document.type` is `purchase_invoice`. Unsupported or missing document types create review findings and no type-specific journal. Monetary values are validated against the accounting `Numeric(18,4)` domain before journal generation; invalid precision, magnitude, zero journal amounts, or negative accounting amounts are not rounded or coerced into persistence. Proposed journals also require a structurally valid three-letter ASCII currency; valid lowercase values are normalized to uppercase, while invalid values are never truncated, guessed, or defaulted.

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

Example extraction request after uploading a synthetic document:

```bash
curl -X POST \
  -H "X-LedgerPilot-Dev-Subject: dev-accountant" \
  -H "X-LedgerPilot-Firm: <synthetic-firm-id>" \
  http://127.0.0.1:8000/api/v1/clients/<synthetic-client-id>/documents/<synthetic-document-id>/extractions
```

Example correction request:

```bash
curl -X POST \
  -H "X-LedgerPilot-Dev-Subject: dev-accountant" \
  -H "X-LedgerPilot-Firm: <synthetic-firm-id>" \
  -H "Content-Type: application/json" \
  -d '{"corrected_raw_value":"RM 100.00","corrected_normalized_value":"100.00","corrected_value_type":"decimal","reason":"Synthetic correction."}' \
  http://127.0.0.1:8000/api/v1/clients/<synthetic-client-id>/documents/<synthetic-document-id>/extractions/<synthetic-run-id>/fields/<synthetic-field-id>/corrections
```

Example accounting decision request:

```bash
curl -X POST \
  -H "X-LedgerPilot-Dev-Subject: dev-accountant" \
  -H "X-LedgerPilot-Firm: <synthetic-firm-id>" \
  http://127.0.0.1:8000/api/v1/clients/<synthetic-client-id>/documents/<synthetic-document-id>/extractions/<synthetic-run-id>/accounting-decisions
```

The response is a recommendation package for future review. It is not an approval, posting, export, payment, or tax/legal opinion.

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
alembic downgrade 0003_phase_3
alembic upgrade head
alembic downgrade 0002_phase_2
alembic upgrade head
alembic downgrade 0001_phase_1
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

PostgreSQL-specific constraint checks:

```bash
python -m pytest tests/integration/test_postgresql_document_constraints.py
python -m pytest tests/integration/test_postgresql_extraction_constraints.py
python -m pytest tests/integration/test_postgresql_accounting_constraints.py
```

## Public Repository Rules

Use synthetic data only. Do not commit real client data, credentials, private keys, `.env` files, PostgreSQL volumes, generated databases, or test output containing secrets.
