# ADR 0012: Append-Oriented Audit-Event Foundation

## Status

Accepted.

## Context

LedgerPilot AI needs attributable security and workflow history, but Phase 1 should not claim cryptographic immutability or production-grade tamper proofing.

## Existing Decision

ADR 0006 requires immutable accounting history. Phase 0 describes audit events as append-only evidence.

## New Evidence

Phase 1 introduces persistence and request correlation IDs.

## Decision

Create an append-oriented audit-event model and service. Normal application interfaces expose event recording and tenant-scoped reads, not update/delete operations. Metadata is screened for sensitive key names.

## Consequences

- Future workflows can record attributable events.
- Tenant-scoped audit queries can be tested early.
- Cryptographic tamper proofing remains future hardening work.

## Risks

- Database administrators can still alter data outside application controls.
- Metadata validation must evolve as event types become richer.

## Follow-up

Add stronger audit-retention and tamper-evidence controls during production hardening.
