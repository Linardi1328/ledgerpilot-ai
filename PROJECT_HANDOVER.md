# Project Handover

## Current Status

**Current status: Phase 5 — Human Review completion (review branch)**

`main` contains the merged Phase 5 first-slice human-review foundation plus the PPO PR validation
adapter. The current review branch completes the planned Phase 5 human-review workflow without
adding export, payment, production OCR/auth/storage, SQL Account, MyInvois, or autonomous
accounting actions.

Phase 4 accounting outputs remain recommendations until an authorised human review outcome is
recorded. Approval never mutates the Phase 4 accounting decision or its proposed journal.

## Phase 5 Completion Scope

This branch adds:

- deterministic review risk classification: `ordinary`, `senior_review_required`, or `blocked`;
- public senior-escalation routing with a required attributable reason;
- reviewer comments;
- client-scoped information requests and submitter responses;
- a client-safe endpoint that exposes only the outstanding information request;
- ordinary accountant approval and senior-only approval for senior-routed work;
- deterministic approval blocking for missing/unbalanced journals and error findings;
- rejection with a required reason;
- immutable `review_outcomes` linked to the exact reviewed decision and proposed journal;
- `corrected_and_approved` outcomes when the reviewed decision was generated after human
  extraction corrections;
- stale-source protection that refuses approval when a newer extraction correction exists after
  the reviewed accounting decision;
- append-only review comments and audit events;
- authorised audit/history views for accountants, senior reviewers, and auditors;
- row locking and database uniqueness/ownership/state constraints for review transitions.

## Human-Supervision Boundary

The system still does not:

- approve based on AI confidence;
- post accounting entries;
- release payments;
- change supplier bank details;
- export to SQL Account;
- submit to MyInvois;
- perform production OCR, authentication, or document storage;
- silently rewrite an approved accounting decision or journal;
- provide unsupervised accounting, tax, or legal judgement.

Approval is an attributable human workflow outcome. The approved outcome references the immutable
Phase 4 decision and proposed journal used during review.

## Correction Rule

Extraction corrections remain append-only.

If a correction existed before the reviewed accounting decision was generated, the decision can be
reviewed and the terminal outcome is recorded as `corrected_and_approved`.

If a correction is created after the accounting decision, that decision is stale for approval. The
reviewer must create a fresh Phase 4 accounting decision and review task. This prevents a human
approval from silently applying to accounting output that did not include the latest corrected
source evidence.

Post-approval correction, reversal, supersession, and export remain later controlled workflows.

## Review and Test Gate

Before this branch can be treated as complete or squash-merged:

- Ruff lint must pass.
- Ruff formatting check must pass.
- Mypy strict checking on `src` must pass.
- Alembic upgrade/downgrade/re-upgrade must pass.
- PostgreSQL document, extraction, accounting, and review constraint tests must pass.
- Full Pytest with the configured coverage threshold must pass.
- Package build must pass.
- PPO PR validation must pass.
- The complete public diff must be reviewed.
- The pull request must remain unmerged until independent review/owner approval.

## Practitioner Validation

The synthetic routing rules in this branch are development controls, not professional accounting or
tax policy. Thresholds, authority limits, tax treatment, and which warnings require senior review
remain subject to practitioner validation before production use.

All fixtures and examples are synthetic. Do not commit real invoices, taxpayer identifiers, bank
details, client records, credentials, secrets, or production data.

## Next Recommended Action

Finish the Phase 5 quality gate, review the complete pull-request diff, and obtain independent
approval before squash-merging to `main`. After Phase 5 is merged, the next roadmap phase is
controlled bank-reconciliation infrastructure; frontend work can proceed in parallel against the
documented Phase 5 API without inventing additional accounting authority.
