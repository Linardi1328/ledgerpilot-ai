# Phase 6 Bank Reconciliation Foundation

## Objective

Phase 6 introduces controlled bank-transaction reconciliation without weakening the human-review boundary established in Phase 5.

The reconciliation flow is:

`synthetic/provider bank data -> deterministic candidates -> human review -> attributable reconciliation outcome`

A candidate score is never an approval signal and never creates a reconciliation outcome by itself.

## Implemented Foundation

The current Phase 6 Draft PR now establishes the provider-independent domain, deterministic matching, and persistence/idempotency boundary:

- immutable-style imported bank transaction value objects;
- provider-attributable import batches;
- a development/test-only synthetic import provider;
- tenant-scoped firm/client ownership on imports, transactions, match runs, candidates, and approved targets;
- exact `Decimal` monetary values with runtime rejection of binary floating point and non-finite values;
- deterministic candidate matching against approved human-review targets;
- hard gates for firm/client ownership, amount, currency, direction, and date window;
- deterministic reference/counterparty evidence used only to rank review candidates;
- explicit persisted `unmatched` versus `candidates_available` match runs;
- matcher name/version lineage even when no candidate is found;
- immutable candidate snapshots retaining the exact target date, direction, amount, currency, reference, counterparty, score, and match reasons used during matching;
- persistent bank import batches and bank transactions;
- database-enforced cross-import idempotency by firm, client, provider, account, and source transaction identifier;
- database-enforced tenant lineage from import batch to transaction to match run to candidate;
- database-enforced candidate linkage to the exact Phase 5 review outcome, decision, and document scope;
- PostgreSQL constraint tests and migration downgrade/re-upgrade coverage.

## Non-Negotiable Invariants

1. No real bank data, credentials, account numbers, statements, or client information are committed.
2. Money uses `Decimal`; `float` monetary inputs are rejected.
3. Cross-firm and cross-client targets can never become reconciliation candidates.
4. Amount, currency, and transaction direction must match exactly in this foundation slice.
5. Candidate generation never produces an approved/reconciled state.
6. Candidate ordering is deterministic for identical inputs.
7. Provider output remains attributable by provider name, version, and batch reference.
8. Re-importing the same provider transaction for the same tenant and account cannot create a duplicate bank transaction.
9. Match attempts remain append-only so an unmatched result is distinguishable from a transaction that has never been evaluated.
10. Human review remains required before any future reconciliation outcome can become terminal.

## Matching Policy

The first matcher is intentionally conservative. A target is considered only when all hard gates pass:

- same firm;
- same client;
- exact amount;
- exact currency;
- exact bank-flow direction;
- booking date within the configured date window.

A deterministic score then uses same/near date, normalized reference evidence, and exact normalized counterparty evidence. The score ranks candidates only. It does not automatically select, approve, or reconcile a transaction.

## Persistence and Idempotency

`bank_import_batches` records provider, account, period, and batch lineage.

`bank_transactions` stores immutable imported transaction evidence. The database rejects a duplicate source transaction identity across different import batches for the same firm, client, provider, and account.

`reconciliation_match_runs` stores each deterministic evaluation attempt, including unmatched attempts, status, matcher name, and matcher version.

`reconciliation_candidates` stores reviewable candidate evidence tied to both the source bank transaction and the exact approved Phase 5 review outcome lineage. Candidate rows are not reconciliation outcomes and have no approval authority.

The persistence slice intentionally does not update or overwrite an earlier match run when matching is repeated. A later run is additional evidence and remains distinguishable from earlier evaluations.

## Deferred to Later Phase 6 Slices

The following remain intentionally unimplemented:

- reconciliation API routes and RBAC permissions;
- review, dispute, approval, or terminal reconciliation outcomes;
- reconciliation audit-event persistence for human actions;
- real bank connectors, OAuth, credentials, or production bank feeds;
- automatic posting, payments, settlement, or external accounting export;
- frontend reconciliation workspace.

These should be added incrementally after the persistence contract passes CI and independent review.

## Testing Direction

Backend accounting, idempotency, migration, and tenant-isolation invariants are tested as part of each Phase 6 development slice.

Broader end-to-end and browser testing of the merged web application remains a later dedicated testing phase, after the Phase 6 API contract and reconciliation workspace are stable.
