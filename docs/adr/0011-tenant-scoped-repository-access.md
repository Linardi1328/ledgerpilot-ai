# ADR 0011: Tenant-Scoped Repository Access

## Status

Accepted.

## Context

Tenant and client isolation are core Phase 1 controls. Repository APIs that retrieve records by ID alone make cross-tenant mistakes easier.

## Existing Decision

Phase 0 requires tenant-owned data to enforce ownership boundaries and client users to access only authorised clients.

## New Evidence

Phase 1 introduces firm and client persistence primitives.

## Decision

Repository methods for tenant-owned records must make firm scope explicit. Client-owned access must validate both firm ownership and explicit client authorisation.

## Consequences

- Call sites show ownership scope directly.
- Tests can assert Firm A cannot access Firm B records and Client A access does not imply Client B access.
- Some repository methods are more verbose by design.

## Risks

- Future generic repositories could weaken the visible scope boundary.

## Follow-up

Preserve scoped repository APIs as document and accounting tables are added.
