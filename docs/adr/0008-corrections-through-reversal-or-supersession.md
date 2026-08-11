# ADR 0008: Corrections Through Reversal or Supersession

## Status

Accepted.

## Context

After approval, accounting records may need correction. Direct edits can hide prior decisions and undermine audit integrity.

## Decision

Approved records must be corrected through controlled workflows. Depending on the situation, the system should use correction, reversal, or supersession while preserving previous values and audit history.

## Alternatives

- Permit direct edits to approved records.
- Forbid all changes after approval.
- Handle corrections only outside LedgerPilot AI.

## Consequences

- Corrections remain attributable and reviewable.
- Workflow and data model must represent relationships between original and corrected records.
- External exports must account for reversal or replacement behaviour.

## Risks

- Users may find correction workflows slower than direct editing.
- Integration platforms may represent reversals differently.

## Follow-up

Validate correction scenarios with accountants before implementing approved-record mutation rules.
