# ADR 0013: GitHub Actions Quality Gate

## Status

Accepted.

## Context

Phase 0 used local verification only. Phase 1 introduces enough infrastructure that automated checks should run on pull requests and pushes to `main`.

## Existing Decision

Phase 0 requires tests before claiming functionality and independent review before merge.

## New Evidence

The repository now has application code, migrations, PostgreSQL dependencies, and tenant-isolation tests.

## Decision

Use GitHub Actions to run Ruff, Ruff format check, Mypy, Alembic migration checks, Pytest with coverage, and package build on pull requests targeting `main` and pushes to `main`.

## Consequences

- Reviewers get repeatable quality signals.
- Migrations are checked against a PostgreSQL service container.
- Coverage has an initial 85% minimum threshold.

## Risks

- CI can still miss environment-specific issues.
- Workflow dependencies must be maintained over time.

## Follow-up

Add dependency/security scanning as production hardening approaches.
