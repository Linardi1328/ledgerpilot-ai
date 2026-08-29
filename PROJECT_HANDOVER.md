# Project Handover

## Current Status

**Current status: Phase 5 complete; Phase 6 bank-reconciliation development started.**

`main` contains the completed Phase 5 backend human-review workflow, the post-approval extraction-evidence lock, and the Phase 5 Next.js Human Review Workspace / Client Submitter Portal. Phase 5 was merged after CI/PPO validation and independent review.

Phase 6 has started on `review/phase-06-bank-reconciliation-foundation` as a deliberately narrow provider-independent domain slice. The first slice does not add real bank integrations, persistence, reconciliation API/RBAC, terminal reconciliation outcomes, payments, posting, or production bank data.

## Phase 5 Closeout

Phase 5 now provides:

- deterministic review risk classification: `ordinary`, `senior_review_required`, or `blocked`;
- attributable review ownership and senior escalation;
- reviewer comments;
- client-scoped information requests and submitter responses;
- ordinary accountant approval and senior-only approval for senior-routed work;
- deterministic approval blocking for missing/unbalanced journals and error findings;
- rejection with a required reason;
- immutable `review_outcomes` linked to the exact reviewed decision and proposed journal;
- `corrected_and_approved` outcomes when source corrections predate the reviewed decision;
- stale-source protection when a correction is newer than the accounting decision;
- append-only review comments and audit events;
- authorised review history for accountants, senior reviewers, and auditors;
- row locking and database constraints around review transitions;
- a post-approval evidence lock that rejects ordinary extraction correction after approval with `approved_record_locked`;
- a Next.js review workspace and client portal using backend-authoritative context, fail-closed live-mode access, exact decimal display checks, and centralized action policies.

## Human-Supervision Boundary

The system still does not:

- approve based on AI confidence;
- autonomously reconcile bank transactions;
- post accounting entries;
- release payments;
- change supplier bank details;
- export to SQL Account;
- submit to MyInvois;
- perform production OCR, authentication, document storage, or bank connectivity;
- silently rewrite an approved accounting decision or journal;
- provide unsupervised accounting, tax, or legal judgement.

Approval remains an attributable human workflow outcome. Phase 6 must preserve the same rule: deterministic bank-match candidates may assist review but cannot themselves become approved reconciliation outcomes.

## Correction Rule

Extraction corrections remain append-only.

If a correction existed before the reviewed accounting decision was generated, the decision can be reviewed and the terminal outcome may be recorded as `corrected_and_approved`.

If a correction is created after the accounting decision, that decision is stale for approval. A reviewer must create a fresh accounting decision and review task.

After an approved outcome exists, ordinary extraction correction is locked. Future post-approval changes require a controlled correction, reversal, or supersession workflow rather than direct mutation.

## Phase 6 Foundation Direction

The initial Phase 6 development order is:

1. Provider-independent bank import value objects and deterministic candidate matching.
2. Persistent bank import/reconciliation models, migrations, tenant constraints, and cross-import idempotency.
3. Reconciliation API and RBAC contract.
4. Human review, dispute, approval, terminal outcome, locking, and audit persistence.
5. Frontend reconciliation workspace against the approved backend contract.
6. Dedicated browser/end-to-end web-app testing once the Phase 6 backend/frontend contract is stable.

The candidate-matching boundary must remain conservative:

- exact-decimal money only;
- firm/client ownership must match;
- candidate scores are explanatory/ranking signals, not approval authority;
- unmatched and disputed transactions must remain visible;
- no automatic payment, posting, settlement, or external export.

## Testing Strategy

Testing is not deferred for accounting invariants: each Phase 6 backend slice must include unit/integration coverage for the behavior it introduces and must pass the repository CI/PPO gates before review.

A broader dedicated web-app testing phase will follow later, after the Phase 6 API contract and reconciliation UI stabilize. That later phase should cover browser-level role isolation, cold-refresh lineage, live/mock authority behavior, reconciliation workflow transitions, accessibility, and end-to-end failure paths without using real financial data.

## Practitioner Validation

All synthetic routing and reconciliation rules are development controls, not professional accounting or banking policy. Thresholds, authority limits, reconciliation tolerances, tax treatment, and production bank-feed behavior require practitioner and security validation before production use.

All fixtures and examples must remain synthetic. Do not commit real invoices, taxpayer identifiers, bank account details, bank statements, client records, credentials, secrets, or production data.

## Next Recommended Action

Independently review and close the Phase 5 documentation PR, while continuing Phase 6 development on its separate review branch. For Phase 6, complete the domain-foundation quality gate first, then move to persistence/idempotency before exposing API or frontend behavior. Do not merge automatically.
