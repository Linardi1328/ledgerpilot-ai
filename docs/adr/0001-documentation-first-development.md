# ADR 0001: Documentation-First Development

## Status

Accepted.

## Context

LedgerPilot AI is at foundation stage. Accountant interviews are still occurring, and premature implementation could encode unvalidated accounting workflows.

## Decision

Phase 0 is documentation-first. It defines purpose, MVP scope, roles, permissions, workflows, states, domain model, requirements, risks, and architecture direction before application features are built.

## Alternatives

- Build a prototype immediately.
- Start with database schema and API routes.
- Wait for all interviews before creating any repository structure.

## Consequences

- Later implementation can trace decisions to documented requirements.
- The project avoids claiming production capability too early.
- Some details remain provisional until validated.

## Risks

- Documentation may become stale if not maintained.
- Excessive documentation could slow validated implementation.

## Follow-up

Review Phase 0 documents after accountant interviews and update requirements before Phase 1+ feature work.
