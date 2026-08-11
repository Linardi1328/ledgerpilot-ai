# ADR 0009: PostgreSQL, SQLAlchemy, and Alembic Foundation

## Status

Accepted.

## Context

Phase 1 needs a persistence foundation for tenant, client, identity, and audit infrastructure. Phase 0 selected Python, SQLAlchemy, Alembic, and PostgreSQL as the initial backend direction.

## Existing Decision

ADR 0002 selected a modular monolith. Phase 0 architecture proposed PostgreSQL, SQLAlchemy, and Alembic.

## New Evidence

Phase 1 now needs concrete migration and repository boundaries before document intake and accounting workflows can be built safely.

## Decision

Use SQLAlchemy 2.x typed ORM models, PostgreSQL as the target database, and Alembic for migrations. Use SQLite only for isolated automated tests where provider-specific PostgreSQL behaviour is not under test.

## Consequences

- Infrastructure tables are versioned through migrations.
- PostgreSQL compatibility remains the implementation target.
- Tests can exercise repository rules without requiring production credentials.

## Risks

- SQLite tests cannot prove every PostgreSQL-specific behaviour.
- Migration discipline must remain strict as accounting tables are added later.

## Follow-up

Continue verifying migrations against PostgreSQL in CI and local development.
