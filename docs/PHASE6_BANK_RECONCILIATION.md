# Phase 6 Bank Reconciliation Foundation

## Objective

Phase 6 introduces controlled bank-transaction reconciliation without weakening the human-review boundary established in Phase 5.

The reconciliation flow is:

`synthetic/provider bank data -> deterministic candidates -> human review -> attributable reconciliation outcome`

A candidate score is never an approval signal and never creates a reconciliation outcome by itself.

## Foundation Slice

This first Phase 6 slice intentionally establishes only the provider-independent domain and deterministic matching boundary:

- immutable-style imported bank transaction value objects;
- provider-attributable import batches;
- a development/test-only synthetic import provider;
- tenant-scoped firm/client ownership on imports, transactions, and approved targets;
- exact `Decimal` monetary values with runtime rejection of binary floating point;
- deterministic candidate matching against approved human-review targets;
- hard gates for firm/client ownership, amount, currency, direction, and date window;
- deterministic reference/counterparty evidence used only to rank review candidates;
- explicit `unmatched` versus `candidates_available` states;
- matcher name/version lineage on each candidate;
- unit tests covering accounting and tenant-isolation invariants.

## Non-Negotiable Invariants

1. No real bank data, credentials, account numbers, statements, or client information are committed.
2. Money uses `Decimal`; `float` monetary inputs are rejected.
3. Cross-firm and cross-client targets can never become reconciliation candidates.
4. Amount, currency, and transaction direction must match exactly in this foundation slice.
5. Candidate generation never produces an approved/reconciled state.
6. Candidate ordering is deterministic for identical inputs.
7. Provider output remains attributable by provider name, version, and batch reference.
8. Human review remains required before any future reconciliation outcome can become terminal.

## Matching Policy

The first matcher is intentionally conservative. A target is considered only when all hard gates pass:

- same firm;
- same client;
- exact amount;
- exact currency;
- exact bank-flow direction;
- booking date within the configured date window.

A deterministic score then uses same/near date, normalized reference evidence, and exact normalized counterparty evidence. The score ranks candidates only. It does not automatically select, approve, or reconcile a transaction.

## Deferred to Later Phase 6 Slices

The following are intentionally not implemented in this foundation slice:

- persistent bank import/reconciliation models and migrations;
- cross-import idempotency enforced by database constraints;
- reconciliation API routes and RBAC permissions;
- review, dispute, approval, or terminal reconciliation outcomes;
- reconciliation audit-event persistence;
- real bank connectors, OAuth, credentials, or production bank feeds;
- automatic posting, payments, settlement, or external accounting export;
- frontend reconciliation workspace.

These should be added incrementally after the domain contract is independently reviewed.

## Testing Direction

Backend accounting and tenant invariants are tested as part of each Phase 6 development slice. Broader end-to-end and browser testing of the merged web application remains a later dedicated testing phase, after the Phase 6 API contract and reconciliation workspace are stable.
