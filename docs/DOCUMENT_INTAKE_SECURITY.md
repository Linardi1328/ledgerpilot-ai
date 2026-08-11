# Document Intake Security

**Current status: Implemented through Phase 2 for local development and automated tests. Not production-ready.**

Phase 2 treats every uploaded document as untrusted binary input until deterministic validation and malware scanning complete successfully.

## Threat Model

Document upload can carry malware, misleading metadata, oversized payloads, path traversal filenames, MIME spoofing, malformed files, and cross-client leakage risk. Phase 2 establishes a narrow intake boundary for synthetic PDF, JPEG, and PNG files only.

## Intake Flow

```text
Untrusted HTTP upload
  -> generated staging key
  -> bounded streaming write
  -> size, filename, MIME, extension, and signature validation
  -> SHA-256 calculation
  -> malware scan
  -> quarantine or accepted storage
  -> document metadata and audit event
```

## Allowed Formats

Only these formats are accepted:

- PDF: `application/pdf`, signature starts with `%PDF-`, extension `.pdf`.
- JPEG: `image/jpeg`, signature starts with JPEG start bytes, extension `.jpg` or `.jpeg`.
- PNG: `image/png`, standard PNG magic bytes, extension `.png`.

DOC, DOCX, XLS, XLSX, ZIP, archive, executable, and macro-enabled formats remain deferred.

## Validation

- Default maximum size: 10 MiB via `LEDGERPILOT_DOCUMENT_MAX_BYTES`.
- Uploads are read in 64 KiB chunks.
- Zero-byte files are rejected.
- Oversized uploads are rejected while streaming and partial staged files are removed.
- Client-supplied MIME type is compared with detected signature.
- Filename extension must match the detected type.
- Submitted filenames are metadata only and are never used as storage paths.
- Path-like filenames, traversal markers, separators, long names, and control characters are rejected where they reach application validation.

Signature validation only confirms initial format compatibility. It does not prove a file is harmless.

## Storage

Phase 2 defines a narrow storage provider boundary and implements only local filesystem storage for development and tests.

Local storage uses:

- `local_storage/staging`
- `local_storage/accepted`
- `local_storage/quarantine`

Storage keys are generated internally from firm, client, document, and random UUID components. Submitted filenames are not part of trusted storage keys. Local promotion uses filesystem rename where available.

Local storage does not provide production encryption-at-rest, redundancy, retention guarantees, or enterprise access control.

## Malware Scanning

Phase 2 defines a scanner provider boundary and implements only `DevelopmentMalwareScanner`.

The development scanner is deterministic and synthetic. It is not real malware protection. It may be enabled only in `development` or `test` with:

```bash
LEDGERPILOT_MALWARE_SCANNER_MODE=development
```

Production rejects this scanner configuration.

## Fail-Closed Behaviour

- Scanner `clean`: file is promoted to accepted storage and metadata status becomes `stored`.
- Scanner `infected`: file is moved to quarantine, normal retrieval is not exposed, and metadata status becomes `quarantined`.
- Scanner `error` or disabled scanner: file is moved to quarantine where possible and metadata status becomes `scan_failed`.

Scanner failure is never treated as clean.

## Tenant and Client Ownership

Upload and metadata endpoints require authentication, RBAC permission, firm scope, and explicit client access. Database constraints enforce document `client_id` ownership through `(client_id, firm_id)` composite foreign keys.

## Audit

Phase 2 records:

- `document_intake_started`
- `document_validation_failed`
- `document_scan_failed`
- `document_quarantined`
- `document_stored`

Audit events include firm, client, actor, target document, request ID where available, and safe metadata. They intentionally exclude file contents, filesystem paths, storage roots, storage keys, scanner internals, credentials, and raw exception details.

## Cleanup

Validation failures and oversize uploads remove staged files. Accepted-storage commit failures attempt to delete the accepted object. Quarantined files are retained under the local quarantine area according to the Phase 2 development policy.

LedgerPilot does not claim distributed atomicity between PostgreSQL and filesystem storage.

## Deferred Production Controls

Before production use, LedgerPilot needs production authentication, production object storage, real malware scanning, encryption-at-rest review, retention/deletion policy, access logging, secure download design, rate limiting, monitoring, backup/restore testing, and incident response procedures.
