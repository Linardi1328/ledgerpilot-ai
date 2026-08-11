# ADR 0014: Staged Document Intake and Trust Boundary

## Status

Accepted.

## Context

Phase 2 introduces document upload. Uploaded documents can contain malware, misleading metadata, large payloads, malformed content, and path traversal filenames. Phase 0 requires document intake to preserve traceability without treating uploaded files as trusted.

## Existing Decision

ADR 0011 requires tenant-scoped access. ADR 0012 requires append-oriented audit events. The security requirements require file validation, size limits, malware scanning, quarantine, and controlled storage.

## Decision

Uploaded documents enter untrusted staging first. The application streams uploads in bounded chunks, validates size and filename, compares declared MIME type with deterministic file signatures, calculates SHA-256, performs malware scanning, and only then promotes clean files to accepted storage.

Files that fail validation are rejected and staged content is removed. Scanner failures fail closed. Infected or scanner-error files are not accepted and may be retained in quarantine according to the development policy.

## Alternatives

- Store uploads directly in accepted storage before validation.
- Trust file extensions or client-supplied MIME type.
- Reject all scanner failures without retaining quarantine evidence.

## Consequences

- Later OCR/extraction can consume only accepted stored documents.
- Validation and scanning outcomes are auditable.
- File storage and database commits still require compensation because filesystem storage and PostgreSQL are not one atomic transaction.

## Risks

- Local development quarantine is not production-grade evidence preservation.
- Signature checks prove only format compatibility, not safety.

## Follow-up

Add production malware scanning, retention policy, secure download design, and operational monitoring before production use.
