# ADR 0003: Decimal Arithmetic for Money

## Status

Accepted.

## Context

Accounting systems require precise monetary calculations. Binary floating-point arithmetic can introduce rounding errors that are unacceptable for invoice totals, tax amounts, journal lines, balances, and reconciliation.

## Decision

Use decimal arithmetic for all monetary values once accounting functionality is implemented. Do not use binary floating-point types for money.

## Alternatives

- Use floating point and round at display time.
- Store integer minor units only.
- Delegate all money calculation to external accounting platforms.

## Consequences

- Monetary invariants can be tested predictably.
- Input parsing, rounding policy, currency precision, and database mapping need careful design.
- Decimal policy must be enforced in code review and tests.

## Risks

- Developers may accidentally introduce floats.
- Currency-specific rounding rules require validation.

## Follow-up

Introduce money value objects or equivalent primitives before implementing invoice arithmetic or journals.
