# ADR 0002: Modular Monolith Initial Architecture

## Status

Accepted.

## Context

LedgerPilot AI needs strong domain consistency across documents, extraction, accounting controls, review, audit history, and integrations. The team should avoid distributed-system complexity before usage patterns are known.

## Decision

Use a modular monolith initially, with clear internal module boundaries and provider abstractions.

## Alternatives

- Microservices from the beginning.
- Single unstructured application module.
- Serverless-only workflow functions.

## Consequences

- Domain transactions and invariants are easier to enforce.
- Local development and testing stay simpler.
- Future service extraction remains possible if justified by scale or ownership.

## Risks

- Poor internal boundaries could still create a tangled monolith.
- Future scaling needs may require refactoring.

## Follow-up

Define module boundaries around identity, documents, extraction, accounting, review, audit, and integrations during Phase 1.
