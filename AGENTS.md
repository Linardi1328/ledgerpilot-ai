# Repository AI Development Rules

These rules apply to all AI-assisted work in this repository.

## Non-Negotiable Rules

- Never use binary floating-point arithmetic for money. Monetary amounts must use decimal arithmetic once implemented.
- Never commit real client data, real invoices, real receipts, real statements, real bank information, taxpayer identifiers, or confidential accounting information.
- Never commit credentials, API keys, tokens, OAuth secrets, private certificates, `.env` files, production databases, or generated secret material.
- Never silently alter approved accounting records. Approved records require controlled correction, reversal, or supersession workflows.
- Treat AI output as untrusted input until deterministic validation and human review are complete.
- Accounting invariants require tests before being treated as implemented behavior.
- Tenant-owned data must enforce ownership boundaries in application logic, persistence, tests, and integrations.
- Accounting and tax rules must remain configurable and independently verifiable.
- Meaningful development occurs on review branches, not directly on `main`.
- Never automatically merge a pull request.
- Never claim untested functionality is working.
- Review the complete public diff before every push.

## Public Repository Policy

This repository is public. Use synthetic examples only. If a file appears to contain real financial, personal, tax, banking, or client information, do not commit it and escalate for review.

## AI Boundary

AI may assist with extraction, classification, recommendation, explanation, and draft preparation. AI must not approve accounting outcomes, bypass deterministic controls, hide uncertainty, or provide unsupervised tax or legal advice.
