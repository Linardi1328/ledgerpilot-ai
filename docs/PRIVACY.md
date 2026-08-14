# Privacy Requirements

This document defines privacy requirements and implementation boundaries. Phase 4 implements tenant/client-scoped document metadata, structured extraction, and accounting decision recommendations for development/testing, but production privacy controls still require independent review.

## Data Minimisation

Collect and process only the information needed for the accounting workflow, legal obligations, and authorised support operations.

## Purpose Limitation

Use client documents, extracted fields, corrections, invoice data, accounting records, and personal information only for authorised LedgerPilot AI purposes.

## Least Access

Restrict access by tenant, client, role, assignment, and workflow need. Auditors and clients receive limited, purpose-specific access.

## Tenant Boundaries

Tenant and client separation is a privacy requirement as well as a security requirement. Firm A must not be able to retrieve Firm B data through authorised application paths.

## Retention

Define retention policies for uploaded documents, extracted fields, recommendations, journals, audit events, logs, exports, and integration responses. Retention must account for accounting, legal, tax, and contractual obligations.

## Secure Deletion

Support secure deletion where permitted. Deletion must not violate required accounting history, audit obligations, or legal holds.

## Confidentiality

Protect confidential accounting information, extracted field values, correction history, personal information, financial information, bank information, taxpayer identifiers, employee information, and integration credentials.

## Sensitive-Log Prevention

Logs should not contain full invoices, extracted values, corrected values, raw OCR text, provider payloads, credentials, tokens, bank details, taxpayer identifiers, or unnecessary personal information. Error messages should be useful without leaking sensitive data.

Phase 4 accounting decision audit events should contain only safe identifiers, engine lineage, counts, status, failure code, and balance state. They must not copy raw invoice values, corrected values, supplier bank details, full recommendation payloads, document content, taxpayer identifiers, or secrets into logs or audit metadata.

## Synthetic Development Data

Development fixtures, examples, documentation samples, tests, screenshots, and demo data must be synthetic. Real client data must not be committed to this public repository.

## Future Legal and Privacy Assessment

Before production use, LedgerPilot AI requires independent review of privacy obligations, data-processing agreements, cross-border processing, retention rules, breach notification duties, and Malaysian privacy requirements.

## Validation Status

**Status: Provisional — requires legal/privacy assessment.**
