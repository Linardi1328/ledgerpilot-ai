# LedgerPilot AI

**Current status: Phase 0 — Foundation, Discovery, and Repository Audit**

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

## Planned Capabilities

- Secure document intake.
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

LedgerPilot must not permanently depend on SQL Account. Phase 0 does not implement the SQL Account API.

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

Create and activate a virtual environment if desired, then install development tooling:

```bash
python -m pip install -e ".[dev]"
```

Run checks:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
python -c "import ledgerpilot"
```

Optional checks:

```bash
python -m pytest --cov
python -m ruff format --check .
python -m build
```

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
- [Privacy Requirements](docs/PRIVACY.md)
- [Risk Register](docs/RISK_REGISTER.md)
- [Roadmap](docs/ROADMAP.md)
- [Glossary](docs/GLOSSARY.md)
- [Architecture Decision Records](docs/adr/README.md)

## Production-Readiness Disclaimer

LedgerPilot AI is not production-ready. Phase 0 is foundation and discovery only. No production accounting workflow, OCR, AI recommendation engine, authentication, database persistence, SQL Account integration, MyInvois integration, or deployment is implemented.

## Accounting, Tax, and Legal Disclaimer

LedgerPilot AI is not a substitute for professional accounting, tax, or legal judgement. Accounting policies, tax handling, Malaysian regulatory requirements, privacy obligations, and MyInvois behaviour must be independently verified before production use.
