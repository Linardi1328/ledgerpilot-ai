# ADR 0007: Synthetic-Data-Only Development

## Status

Accepted.

## Context

The repository is public and accounting data is sensitive. Real client records, invoices, receipts, statements, bank details, taxpayer identifiers, employee information, and credentials must not be exposed.

## Decision

Use synthetic development data only. Do not commit real client data or credentials.

## Alternatives

- Use anonymised real data.
- Store private fixtures in the public repository.
- Depend on developer-local real documents.

## Consequences

- Public repository risk is reduced.
- Synthetic fixtures must be designed carefully to cover realistic cases.
- Any future real-data use requires separate controls outside this repository.

## Risks

- Poor synthetic fixtures may miss production edge cases.
- Developers may accidentally paste sensitive data into issues, logs, or examples.

## Follow-up

Create fixture review rules and sensitive-data checks before adding sample documents or datasets.
