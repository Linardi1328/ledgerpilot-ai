# LedgerPilot AI

**Current status: Phase 2 — Secure Document Intake (review branch)**

LedgerPilot AI is a planned accounting automation assistant for reducing repetitive bookkeeping and accounting work while preserving deterministic accounting controls, traceability, and human review.

It is intended to assist accountants, not replace professional judgement.

## Problem

Accounting teams spend significant time on repetitive work such as invoice and receipt processing, data entry, transaction categorisation, journal preparation, supplier/customer matching, duplicate-document detection, missing-information requests, exception review, bank reconciliation, month-end preparation, supporting-document management, and audit-history maintenance.

LedgerPilot AI aims to reduce this repetitive work while keeping accountants in control of judgement-heavy and high-risk decisions.

## Core Operating Principle

> AI for extraction and recommendations + deterministic accounting controls + human approval for exceptions.

AI output is treated as untrusted input until validated. Recommendations must remain explainable, reviewable, and subordinate to deterministic controls.

## Vision

LedgerPilot AI should become a controlled workflow assistant for accounting firms and their clients. It should help move supporting documents from intake to reviewable accounting entries while preserving evidence, uncertainty, approval history, and correction history.

## First MVP: Prototype 1 - Invoice-to-Review

```text
Synthetic Purchase Invoice
        |
        v
Field Validation
        |
        v
Duplicate Detection
        |
        v
Supplier Matching
        |
        v
Accounting Recommendation
        |
        v
Balanced Journal Suggestion
        |
        v
Confidence & Risk Assessment
        |
        v
Accountant Review
        |
        v
Approve / Correct / Reject / Escalate
        |
        v
Audit History
```

Initial MVP scope includes synthetic purchase invoices, manual structured input, document abstraction, required-field validation, arithmetic validation, duplicate detection, supplier matching, configurable accounting rules, GL-account recommendations, tax-code and cost-centre recommendation interfaces, balanced journal suggestions, confidence/risk information, accountant review, senior escalation, approval, correction, rejection, comments, information requests, audit-event recording, and a provider-independent future export interface.

## Non-Goals for the Initial MVP

- Real client information.
- Payment execution.
- Supplier-bank-detail changes.
- Autonomous high-risk posting.
- Unsupervised accounting judgement.
- Unsupervised tax advice.
- Full bank reconciliation.
- Real SQL Account integration.
- Production MyInvois integration.
- Custom ML model training.
- Enterprise reporting.
- Payroll.
- Complex frontend.
- Native mobile application.

## Users

- Firm Administrator.
- Accountant.
- Senior Reviewer.
- Client / Document Submitter.
- Auditor / Read-Only User.

See [Role and Permission Model](docs/ROLE_PERMISSION_MODEL.md).

## Implemented Through Phase 2

The Phase 2 review branch establishes the secure document-intake boundary:

- FastAPI application factory and `/api/v1` routing.
- Typed Pydantic settings with guarded environment/auth/storage/scanner configuration.
- PostgreSQL-targeted SQLAlchemy 2.x persistence and Alembic migrations.
- Firm, user, membership, client, client-access, audit-event, document, and document-file primitives.
- Development-only authentication boundary backed by persisted memberships.
- RBAC role and permission definitions aligned with Phase 0.
- Tenant/client-scoped repository access patterns.
- Health/readiness endpoints.
- Safe structured API errors and request correlation IDs.
- Secure upload endpoint for PDF, JPEG, and PNG documents.
- Protected safe document-metadata endpoint.
- Bounded streaming upload, size enforcement, SHA-256 hashing, filename validation, MIME/signature/extension checks, staging, quarantine, accepted storage, and audit events.
- Provider-independent document-storage and malware-scanner boundaries with local development/test implementations only.
- GitHub Actions CI quality gate.

Phase 2 does not implement invoice extraction, OCR, AI providers, accounting recommendations, journals, review queues, bank reconciliation, SQL Account, MyInvois, frontend work, production authentication, production object storage, production malware scanning, or production deployment.

## Planned Capabilities

- Production-grade document storage, malware scanning, retention, and secure retrieval.
- OCR and structured extraction through provider-independent interfaces.
- Required-field and arithmetic validation.
- Duplicate-document detection.
- Supplier/customer matching.
- Configurable accounting recommendations.
- Balanced journal suggestions.
- Confidence and risk indicators.
- Review routing, escalation, approval, correction, rejection, and information requests.
- Audit history.
- Future accounting-platform export.
- Future Malaysian MyInvois/e-Invoice support.

## Accounting Controls

LedgerPilot must never allow AI to independently release payments, change supplier bank details, silently alter approved accounting records, bypass required approval, make complex accounting judgements without human review, provide unsupervised tax/legal advice, hide uncertainty, or treat AI output as inherently correct.

Core accounting invariants:

- All monetary calculations must eventually use decimal arithmetic, never binary floating-point arithmetic.
- A journal cannot be approved unless total debits equal total credits.
- Accounting entries retain linkage to source evidence.
- Approved records cannot be silently overwritten.
- Corrections preserve previous values and history.
- AI recommendations cannot bypass deterministic validation.

See [Accounting-Control Principles](docs/ACCOUNTING_PRINCIPLES.md).

## Security Principles

Future implementation must address authentication, authorisation, RBAC, least privilege, tenant isolation, client isolation, encryption in transit, encryption at rest, secret management, session security, file validation, file-type allowlists, file-size limits, malware scanning, quarantine, document storage, temporary/signed access, audit logging, log redaction, rate limiting, retention, secure deletion, backup, recovery, disaster recovery, incident response, dependency security, and security testing.

See [Security Requirements](docs/SECURITY.md).

## Privacy Warning

This public repository must contain synthetic development data only. Do not commit real client data, real invoices, receipts, statements, bank information, supplier bank details, taxpayer identifiers, MyInvois identifiers, employee information, confidential accounting information, production databases, `.env` files, passwords, API keys, tokens, OAuth credentials, or private certificates.

See [Privacy Requirements](docs/PRIVACY.md).

## Malaysian Context

Future support may include MYR, Malaysian business identifiers, taxpayer identifiers, configurable Malaysian tax rules, SST-related configuration, LHDN MyInvois, e-Invoice submission, validation status, rejection, cancellation, validated identifiers, and integration audit history.

Current Malaysian accounting, taxation, privacy, and MyInvois rules must be independently verified before production use.

## SQL Account Direction

SQL Account is the first proposed external accounting-platform integration:

```text
LedgerPilot AI
      |
      v
Human Approved Transaction
      |
      v
AccountingPlatformGateway
      |
      v
SQLAccountGateway
      |
      v
SQL Account
```

LedgerPilot must not permanently depend on SQL Account. The SQL Account API is not implemented.

## Secure Document Intake

Supported Phase 2 upload formats are deliberately limited:

- PDF: `application/pdf`, `%PDF-` signature, `.pdf` extension.
- JPEG: `image/jpeg`, JPEG start signature, `.jpg` or `.jpeg` extension.
- PNG: `image/png`, PNG magic bytes, `.png` extension.

The upload boundary treats every file as untrusted binary input. Submitted filenames are metadata only and are never used as storage paths. Uploads are streamed in bounded chunks, rejected if empty or larger than `LEDGERPILOT_DOCUMENT_MAX_BYTES`, hashed with SHA-256, checked for declared MIME/signature/extension consistency, scanned through the malware-scanner boundary, and either promoted to accepted storage or quarantined/fail-closed.

The implemented endpoints are:

- `POST /api/v1/clients/{client_id}/documents`
- `GET /api/v1/clients/{client_id}/documents/{document_id}`

There is no raw document download endpoint in Phase 2.

Local filesystem storage and the deterministic development malware scanner are for local development and automated tests only. They are not production storage or production malware protection. See [Document Intake Security](docs/DOCUMENT_INTAKE_SECURITY.md).

## Proposed Technology

Backend direction:

- Python 3.12.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- Alembic.
- PostgreSQL.

Quality tooling:

- Pytest.
- Ruff.
- Mypy.

Future optional components:

- Redis.
- Celery or alternative queue.
- React.
- TypeScript.
- OCR providers such as Tesseract, PaddleOCR, cloud document-processing APIs, or local machine-learning models.

The initial architecture direction is a modular monolith, not microservices.

See [Architecture](docs/ARCHITECTURE.md).

## Repository Structure

```text
ledgerpilot-ai/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── docs/
│   ├── adr/
│   ├── ACCEPTANCE_CRITERIA.md
│   ├── ACCOUNTING_PRINCIPLES.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   ├── DOCUMENT_INTAKE_SECURITY.md
│   ├── DOMAIN_MODEL.md
│   ├── GLOSSARY.md
│   ├── MVP_SCOPE.md
│   ├── NON_FUNCTIONAL_REQUIREMENTS.md
│   ├── PRIVACY.md
│   ├── PROJECT_CHARTER.md
│   ├── REQUIREMENTS.md
│   ├── RISK_REGISTER.md
│   ├── ROADMAP.md
│   ├── ROLE_PERMISSION_MODEL.md
│   ├── SECURITY.md
│   └── WORKFLOWS.md
├── src/ledgerpilot/
├── tests/
├── AGENTS.md
├── CONTRIBUTING.md
├── LICENSE
├── PROJECT_HANDOVER.md
├── README.md
└── pyproject.toml
```

## Local Development

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

Install the package and development tooling:

```bash
python -m pip install -e ".[dev]"
```

Start local PostgreSQL:

```bash
docker compose up -d postgres
```

Configure local-only document intake:

```bash
export LEDGERPILOT_DOCUMENT_STORAGE_BACKEND=local
export LEDGERPILOT_DOCUMENT_STORAGE_ROOT=local_storage
export LEDGERPILOT_MALWARE_SCANNER_MODE=development
export LEDGERPILOT_DOCUMENT_MAX_BYTES=10485760
```

Apply migrations:

```bash
alembic upgrade head
```

Run the API locally:

```bash
uvicorn ledgerpilot.api.app:create_app --factory --reload
```

Run checks:

```bash
python -m pytest
python -m pytest --cov=ledgerpilot --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
```

Stop local PostgreSQL:

```bash
docker compose down
```

See [Development Guide](docs/DEVELOPMENT.md).

## Contribution Workflow

```text
main
  |
  v
review/<phase-or-task>
  |
  v
implementation
  |
  v
verification
  |
  v
push
  |
  v
pull request
  |
  v
independent review
  |
  v
owner approval
  |
  v
merge
```

Do not perform normal development directly on `main`. Do not automatically merge. See [Contributing](CONTRIBUTING.md).

## Roadmap

1. Repository Bootstrap.
2. Phase 0 - Foundation and Discovery.
3. Phase 1 - Core Infrastructure.
4. Phase 2 - Secure Document Intake.
5. Phase 3 - OCR and Extraction.
6. Phase 4 - Accounting Decision Engine.
7. Phase 5 - Human Review.
8. Phase 6 - Bank Reconciliation.
9. Phase 7 - Accounting Integrations / SQL Account.
10. Phase 8 - Malaysian MyInvois.
11. Phase 9 - Analytics and ML.
12. Phase 10 - Production Hardening.
13. Future Accounting Firm Pilot.

See [Roadmap](docs/ROADMAP.md).

## Documentation

- [Project Charter](docs/PROJECT_CHARTER.md)
- [MVP Scope](docs/MVP_SCOPE.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Non-Functional Requirements](docs/NON_FUNCTIONAL_REQUIREMENTS.md)
- [Acceptance Criteria](docs/ACCEPTANCE_CRITERIA.md)
- [Domain Model](docs/DOMAIN_MODEL.md)
- [Workflows](docs/WORKFLOWS.md)
- [Role and Permission Model](docs/ROLE_PERMISSION_MODEL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Accounting-Control Principles](docs/ACCOUNTING_PRINCIPLES.md)
- [Security Requirements](docs/SECURITY.md)
- [Document Intake Security](docs/DOCUMENT_INTAKE_SECURITY.md)
- [Privacy Requirements](docs/PRIVACY.md)
- [Risk Register](docs/RISK_REGISTER.md)
- [Roadmap](docs/ROADMAP.md)
- [Glossary](docs/GLOSSARY.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Architecture Decision Records](docs/adr/README.md)

## Production-Readiness Disclaimer

LedgerPilot AI is not production-ready. Phase 2 establishes backend infrastructure and a local-development secure document-intake boundary for review only. Production authentication, production deployment, production object storage, production malware scanning, OCR, AI recommendation engine, accounting automation, SQL Account integration, and MyInvois integration are not implemented.

## Accounting, Tax, and Legal Disclaimer

LedgerPilot AI is not a substitute for professional accounting, tax, or legal judgement. Accounting policies, tax handling, Malaysian regulatory requirements, privacy obligations, and MyInvois behaviour must be independently verified before production use.
