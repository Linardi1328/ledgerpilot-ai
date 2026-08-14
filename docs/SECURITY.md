# Security Requirements

This document defines security requirements and implementation boundaries. Phase 4 implements local-development secure document intake, structured extraction, and accounting decision recommendations only; most production security controls remain planned and must not be claimed as production-ready.

## Authentication

- Require authenticated access for non-public application functions.
- Support secure password/session handling or a trusted identity provider in future phases.
- Require multi-factor authentication consideration for firm administrators and privileged users.

## Authorisation and RBAC

- Enforce role-based access control.
- Apply least privilege.
- Separate administrative access from accounting approval authority.
- Enforce tenant and client isolation on every authorised application path.
- Prevent client users from accessing other clients.

## Tenant and Client Isolation

- Every tenant-owned record must be scoped to a firm or client entity.
- Queries, commands, exports, logs, and audit views must prevent cross-client leakage.
- Tests must cover tenant/client isolation once persistence and APIs exist.

## Data Protection

- Use encryption in transit.
- Use encryption at rest for production data stores and document storage.
- Manage secrets outside source control.
- Rotate secrets and integration credentials when required.
- Redact secrets and sensitive data from logs.

## Session Security

- Use secure cookies or token handling.
- Apply session expiry and revocation.
- Protect against cross-site request forgery where browser sessions are used.
- Record privileged session activity in audit logs where appropriate.

## File Security

- Validate uploaded files.
- Use a file-type allowlist.
- Enforce file-size limits.
- Perform malware scanning.
- Quarantine suspicious files.
- Store original files in controlled document storage.
- Use temporary or signed access for file retrieval.
- Prevent direct public access to private documents.

Phase 2 implements the first document-intake boundary for PDF, JPEG, and PNG files with bounded streaming, SHA-256 metadata, signature/MIME/extension checks, local staging, quarantine, local accepted storage, and a guarded deterministic development scanner. See [Document Intake Security](DOCUMENT_INTAKE_SECURITY.md). Production object storage, real malware scanning, signed download access, retention automation, and production hardening remain future work.

## Extraction Security

- Treat OCR/extraction output as untrusted provider observations.
- Validate provider output shape, field count, field paths, value lengths, value types, confidence range, page numbers, and source locators before persistence.
- Reject provider-controlled tenant/client/document/run/storage identifiers.
- Persist source SHA-256 and provider lineage for each extraction run.
- Do not persist raw provider payloads, full OCR text, provider headers, credentials, storage keys, or filesystem paths by default.
- Do not log full extracted values or corrected values.
- Permit extraction only from stored documents with accepted `DocumentFile` records.
- Require `RUN_EXTRACTION` for extraction triggers and `CORRECT_EXTRACTED_INFORMATION` for corrections.

Phase 3 implements only a guarded deterministic development extraction provider. It is not real OCR and production refuses it through settings validation. Production OCR providers, provider timeouts, retry policy, rate limiting, and provider privacy/security assessment remain future work.

## Accounting Decision Security

- Treat recommendation and rule output as untrusted until deterministic validation and human review are complete.
- Permit accounting decision execution only for roles with `RUN_ACCOUNTING_DECISION`.
- Do not grant Firm Admin implicit accounting execution authority.
- Reject pending, running, failed, or non-downstream-ready extraction runs before decision execution.
- Use effective extraction values for computation while preserving original provider observations.
- Enforce firm/client/document/extraction scope in application logic and database constraints.
- Do not log raw invoice values, corrected values, unrestricted recommendation payloads, supplier bank details, taxpayer identifiers, or document content.
- Record only safe audit metadata for accounting decision start, success, and failure events.
- Keep synthetic rule configuration clearly separated from practitioner-validated production policy.

## Audit Logging

- Record security-relevant and accounting-control events.
- Include actor, tenant/client scope, action, target, timestamp, result, and reason when available.
- Protect audit logs from unauthorised modification.
- Redact sensitive values.

## Abuse Protection

- Apply rate limiting to authentication, upload, extraction, and integration endpoints.
- Monitor suspicious upload and access patterns.
- Protect against brute force, scraping, and excessive automation.

## Retention and Deletion

- Define retention policies per tenant/client and record type.
- Support secure deletion where legally and operationally permitted.
- Preserve accounting history where retention obligations require it.

## Backup and Recovery

- Define backup frequency, retention, restoration procedures, and recovery objectives.
- Test restoration before claiming recoverability.
- Include disaster recovery planning before production use.

## Incident Response

- Define incident classification, containment, investigation, notification, remediation, and post-incident review.
- Include credential exposure, cross-client leakage, malware upload, data loss, and integration compromise scenarios.

## Financial and Personal Information

- Treat invoices, receipts, bank data, taxpayer identifiers, employee information, and accounting records as sensitive.
- Minimise exposure in logs, exports, test fixtures, and support workflows.

## Integration Secrets

- Store accounting-platform, OCR, AI, storage, and MyInvois credentials in a secrets manager or equivalent secure facility.
- Do not store secrets in source code, `.env.example`, documentation, logs, test fixtures, or issue reports.

## Dependency Security

- Pin or constrain dependencies appropriately.
- Monitor dependency vulnerabilities.
- Review transitive dependencies before production use.
- Run dependency/security testing as the project matures.

## Security Testing

Future security testing should include unit tests, integration tests, tenant-isolation tests, access-control tests, file-validation tests, provider-output validation tests, secret-scanning checks, dependency scanning, and penetration testing before production use.

## Validation Status

**Status: Provisional — requires technical investigation, legal/privacy review, and production security design.**
