# ADR 0019: Append-Only Extraction Corrections

## Status

Accepted

## Context

Provider extraction output is not accounting truth, but reviewers need to correct extracted values before future accounting validation. Rewriting original extracted fields would hide uncertainty and undermine auditability.

## Decision

Keep original extracted fields immutable through normal application interfaces. Store human corrections as append-only `ExtractionFieldCorrection` records with firm/client/document/run/field scope, actor attribution, reason, timestamp, and revision number.

The latest correction is exposed as the effective value, while the original provider value and confidence remain visible.

## Alternatives

- Update extracted fields in place.
- Store only the latest corrected value.
- Defer corrections until accounting review is implemented.

## Consequences

- Correction history is attributable and reviewable.
- Provider confidence remains tied to the original observation.
- Future accounting validation can consume effective values without losing provenance.

## Risks

- Concurrency around revision numbers may need stronger handling as usage grows.
- Correction values are sensitive and must not be logged or copied into audit metadata.

## Follow-Up

Add concurrency controls, retention policy, reviewer UX, and Phase 4 validation rules before production use.
