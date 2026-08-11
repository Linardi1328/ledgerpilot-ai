# ADR 0017: Provider-Independent Extraction Boundary

## Status

Accepted

## Context

Phase 3 needs structured extraction without coupling LedgerPilot to a commercial OCR, AI, or document-processing vendor. Phase 0 requires provider independence and treats provider output as untrusted input.

## Decision

Define a narrow `ExtractionProvider` boundary. Providers receive only an accepted source file plus controlled context and return provider-independent field observations. The application owns tenant/client/document/run identifiers, storage keys, actor attribution, run state, persistence, audit events, and permissions.

Phase 3 implements only a deterministic `DevelopmentExtractionProvider` for development and automated tests. Production rejects this provider through settings validation.

## Alternatives

- Couple directly to a cloud OCR response schema.
- Store provider raw payloads and interpret them later.
- Delay extraction persistence until a real OCR provider is selected.

## Consequences

- Core persistence and accounting logic remain independent of OCR vendor choice.
- CI can test the complete pipeline without paid services or credentials.
- Production OCR accuracy is not claimed in Phase 3.

## Risks

- The development provider can be mistaken for real OCR if documentation is ignored.
- Future provider adapters must carefully translate vendor-specific output into the internal contract.

## Follow-Up

Select and review production OCR providers, timeout behaviour, retry policy, data-processing terms, and privacy controls in a later phase.
