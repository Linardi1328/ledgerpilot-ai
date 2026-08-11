# ADR 0006: Immutable Accounting History

## Status

Accepted.

## Context

Accounting and audit workflows require traceability. Approved records should not be silently changed after review.

## Decision

Approved accounting records are immutable for normal mutation paths. Later changes must preserve history through controlled correction, reversal, or supersession workflows.

## Alternatives

- Allow direct updates with last-write-wins behaviour.
- Store only current values.
- Rely on database backups for history.

## Consequences

- Auditability is stronger.
- Data model and workflows must represent versions and decisions.
- User experience must clearly explain current versus historical records.

## Risks

- Implementation complexity increases.
- Poorly designed history views could confuse users.

## Follow-up

Design audit-event and correction models before implementing approval persistence.
