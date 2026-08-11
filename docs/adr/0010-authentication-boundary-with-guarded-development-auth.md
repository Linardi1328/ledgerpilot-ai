# ADR 0010: Authentication Boundary With Guarded Development Auth

## Status

Accepted.

## Context

Phase 1 must establish authentication boundaries without inventing an insecure production password system.

## Existing Decision

Phase 0 requires authenticated access, RBAC, least privilege, tenant isolation, and no unsupported production-readiness claims.

## New Evidence

Automated tests and local development need a way to construct principals before a production identity provider exists.

## Decision

Define a typed authentication backend boundary. Provide only a guarded development-header backend for development and test environments. It is disabled by default, refused in production, and loads role, permissions, membership, and client access from persistence rather than trusting request headers.

## Consequences

- Local tests can validate protected routes and RBAC.
- Production authentication remains explicitly deferred.
- Header-based development auth cannot grant arbitrary roles or client access.

## Risks

- Misconfiguration could be dangerous if production guards are weakened later.
- A future production identity provider still needs careful design.

## Follow-up

Replace development auth with a production identity-provider integration before production use.
