# OCR and Structured Extraction

**Current status: Implemented through Phase 3 for local development and automated tests. Not production-ready.**

Phase 3 turns an already accepted, safely stored document into validated structured extraction results. It does not implement production OCR or accounting automation.

## Trust Boundary

Extraction provider output is treated as untrusted observations. Provider confidence is not proof, and normalized values are not approved accounting data.

Providers cannot choose tenant identifiers, client identifiers, document identifiers, extraction run identifiers, document-file identifiers, storage keys, actor attribution, permissions, or run status. Application code controls those values.

Phase 3 persists only LedgerPilot's validated internal representation. It does not persist raw provider responses, full OCR text, provider HTTP headers, credentials, storage keys, or filesystem paths.

## Source Eligibility

Extraction may consume only:

- `Document.status == stored`
- an associated `DocumentFile.storage_area == accepted`
- firm/client scope authorised through the authenticated principal

Extraction is denied for uploaded, validating, validation-failed, scan-pending, scanning, scan-failed, quarantined, or rejected documents. Extraction never reads staging or quarantine storage.

The extraction run retains:

- firm ID
- client ID
- document ID
- document-file ID
- source SHA-256 copied from the accepted `DocumentFile`

## Provider Boundary

Phase 3 defines an `ExtractionProvider` interface. A provider receives an opened accepted source file plus controlled request context. It returns provider-independent field observations.

Every run records provider lineage:

- provider name
- provider version
- optional model version
- extraction schema version

The only implemented provider is `DevelopmentExtractionProvider`. It is deterministic, synthetic, requires no credentials, performs no network call, and is allowed only in `development` or `test`. Production configuration rejects it.

## Run Lifecycle

Extraction runs use this lifecycle:

```text
pending -> running -> succeeded
pending -> running -> failed
```

Terminal runs are not reset. A retry creates a new `ExtractionRun`.

Only `succeeded` runs are downstream-ready. `pending`, `running`, and `failed` runs are not eligible for Phase 4 accounting validation.

## Field Model

Extracted fields use provider-independent paths such as:

- `document.type`
- `supplier.name`
- `invoice.number`
- `invoice.date`
- `invoice.currency`
- `invoice.total`
- `invoice.lines[0].description`

Within a run, each field path is unique. Repeated line data should use explicit indexed paths.

Each field may retain:

- raw provider value
- optional normalized candidate value
- value type
- optional confidence
- source page number
- optional provider-neutral source locator

Monetary candidates are represented as strings/decimal-normalized strings, never binary floating-point values.

## Validation

Provider output must pass deterministic validation before persistence:

- maximum field count
- field-path length and format
- duplicate paths
- provider-controlled identity path rejection
- value-type allowlist
- maximum raw/normalized value length
- confidence range `0.0000` to `1.0000`
- positive source page numbers
- source locator size and shape
- deterministic normalized decimal/date/integer/boolean validation

Malformed output fails the run and persists no successful fields.

## Corrections

Original provider fields are immutable through normal application interfaces. A correction creates an append-only `ExtractionFieldCorrection` record with:

- field/run/document/client/firm ownership
- corrected-by user and membership
- revision number
- corrected raw value
- optional corrected normalized value
- corrected value type
- required reason
- timestamp

The latest correction becomes the effective value for API responses. Provider confidence remains unchanged.

## Audit

Phase 3 records:

- `extraction_started`
- `extraction_succeeded`
- `extraction_failed`
- `extraction_correction_recorded`

Audit metadata may include run ID, document ID, document-file ID, provider lineage, field count, field ID, revision number, and safe failure code.

Audit metadata must not include extracted values, corrected values, full OCR text, raw provider payloads, storage keys, filesystem paths, credentials, or provider secrets.

## API

Implemented endpoints:

- `POST /api/v1/clients/{client_id}/documents/{document_id}/extractions`
- `GET /api/v1/clients/{client_id}/documents/{document_id}/extractions`
- `GET /api/v1/clients/{client_id}/documents/{document_id}/extractions/{run_id}`
- `POST /api/v1/clients/{client_id}/documents/{document_id}/extractions/{run_id}/fields/{field_id}/corrections`

Running extraction requires `RUN_EXTRACTION`. Viewing extraction output currently uses `VIEW_DOCUMENTS` plus client scope. Corrections require `CORRECT_EXTRACTED_INFORMATION`.

## Limitations

- The development provider is not real OCR.
- No production OCR provider is implemented.
- Extraction is synchronous in Phase 3.
- No raw OCR text endpoint exists.
- No raw document download endpoint exists.
- Extraction itself does not perform accounting recommendations, invoice validation, journal generation, approval workflow, SQL Account export, or MyInvois integration. Phase 4 consumes eligible extraction runs for recommendation-only accounting decisions.
- Production deployments still need production authentication, production object storage, production malware scanning, provider timeout/retry controls, rate limiting, monitoring, and privacy/security review.
