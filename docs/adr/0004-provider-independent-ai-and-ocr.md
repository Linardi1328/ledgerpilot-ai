# ADR 0004: Provider-Independent AI and OCR

## Status

Accepted.

## Context

OCR, extraction, and AI recommendation providers may change for cost, accuracy, privacy, availability, or regulatory reasons. Core accounting logic must remain stable if providers change.

## Decision

Use provider-independent interfaces for OCR, structured extraction, document classification, and AI recommendations. Provider output is treated as untrusted input.

## Alternatives

- Couple directly to one commercial AI provider.
- Avoid AI providers entirely.
- Build custom ML models immediately.

## Consequences

- Providers can be swapped or disabled.
- Tests can use fakes and synthetic fixtures.
- More interface design is required.

## Risks

- Abstractions may be overbuilt before real provider constraints are known.
- Provider-specific strengths may be hidden by the interface.

## Follow-up

Define minimal provider contracts when Phase 3 begins and validate them with realistic synthetic documents.
