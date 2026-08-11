# ADR 0018: Immutable Extraction Runs and Fields

## Status

Accepted

## Context

Extraction providers may misread, omit, or hallucinate fields. LedgerPilot needs traceability from each extracted field back to the source document, document file, source hash, provider, version, run status, and confidence.

## Decision

Represent each extraction attempt as a new `ExtractionRun`. Persist validated fields as original provider observations. Do not reset terminal runs or overwrite prior runs when extraction is retried.

Only succeeded runs are downstream-ready. Pending, running, and failed runs cannot be treated as ready for future accounting validation.

## Alternatives

- Update one mutable extraction record per document.
- Treat the latest run as automatically authoritative.
- Persist fields from malformed provider output and flag partial success.

## Consequences

- Multiple provider attempts remain traceable.
- Failed output cannot silently become downstream input.
- Future review logic can choose an appropriate run explicitly instead of assuming newest is best.

## Risks

- More records are stored over time.
- Future UI/API work must present run history clearly.

## Follow-Up

Define retention policy, run-selection rules, and asynchronous processing strategy in later phases.
