# ADR 0015: Provider-Independent Document Storage

## Status

Accepted.

## Context

LedgerPilot must store original supporting documents without committing binaries into PostgreSQL. Future production deployments may use S3-compatible storage, Azure Blob Storage, Google Cloud Storage, or another controlled document store.

## Existing Decision

ADR 0002 selects a modular monolith with clear internal provider boundaries. Phase 0 requires provider independence for document storage and future processing.

## Decision

Define a narrow `DocumentStorage` boundary for staging, promotion, quarantine, deletion, existence checks, and internal opening of accepted objects for future processing. Implement only local filesystem storage in Phase 2 for development and automated tests.

Storage keys are generated internally and never use submitted filenames.

## Alternatives

- Store uploaded binaries directly in PostgreSQL.
- Couple Phase 2 directly to a cloud object-storage vendor.
- Expose arbitrary storage-key retrieval to application callers.

## Consequences

- The database stores metadata and traceability, while storage providers store binary content.
- Future production object storage can replace the local provider behind the boundary.
- Local storage remains explicitly non-production.

## Risks

- Filesystem storage and database metadata are not transactionally atomic.
- Local storage does not provide production encryption, redundancy, or retention controls.

## Follow-up

Design production object storage, encryption, signed access, retention, and backup controls before production use.
