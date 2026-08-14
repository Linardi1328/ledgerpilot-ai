# Accounting Decision Engine

**Current status: Implemented in Phase 4 review branch for local development and automated tests. Not production-ready.**

Phase 4 converts a successful, downstream-ready structured extraction into a versioned accounting decision run. A decision run contains deterministic validation findings, supplier-match candidates, duplicate candidates, synthetic recommendations, and an optional proposed journal for future human review.

Phase 4 recommendations are not approvals. Human approval, rejection, review routing, comments, information requests, export, SQL Account integration, MyInvois integration, and payment workflows remain future work.

## Eligibility

Only extraction runs with `status == succeeded` and downstream-ready semantics may enter the accounting decision engine. Pending, running, failed, or non-downstream-ready extraction runs are rejected before an accounting decision run is created.

## Supported Document Types

Phase 4 currently supports `purchase_invoice` only for purchase-invoice-specific accounting recommendations and proposed journals.

If `document.type` is missing, the run records a required-field finding and does not generate purchase-invoice recommendations or a proposed journal. If `document.type` is present but unsupported, such as `receipt`, the run records `unsupported_document_type` and does not perform supplier accounting mapping, purchase-invoice recommendations, or purchase-invoice journal generation.

Unsupported document types are reviewable decision attempts, not infrastructure failures.

The decision run retains:

- Firm, client, document, and extraction-run scope.
- Initiating actor and membership.
- Engine name and version.
- Source document hash copied from the extraction run.
- Pending, running, succeeded, or failed status.
- Started, completed, and created timestamps.
- Safe failure code and request ID.

Rerunning the decision engine creates a new immutable attempt. Completed decision runs are not reset or overwritten.

## Effective Values

The engine consumes effective extraction values. The latest `ExtractionFieldCorrection` for a field overrides the provider value for downstream computation, while the original `ExtractedField` value, confidence, and provenance remain unchanged.

The engine does not invent missing values.

## Deterministic Validation

Implemented validation is provider-independent and uses Decimal arithmetic for monetary values.

For synthetic purchase invoices, required fields include:

- `document.type`
- `supplier.name`
- `invoice.number`
- `invoice.date`
- `invoice.currency`
- `invoice.total`

Where subtotal and tax fields are available, arithmetic validation checks:

```text
invoice.subtotal + invoice.tax == invoice.total
```

Mismatches become structured findings. Extracted values are not silently changed.

Accounting-domain monetary values are validated before proposed journal generation and persistence. Values must parse as finite Decimal values, fit exactly in the persisted `Numeric(18,4)` domain, and avoid unsupported fractional precision. Journal-line debit or credit amounts must be strictly greater than zero. LedgerPilot does not silently round, coerce, or normalize invalid monetary values to make them fit persistence; invalid values produce `invalid_monetary_value` findings and no proposed journal.

Proposed journal currency is also validated before journal generation and persistence. Phase 4 accepts only structurally valid three-letter ASCII alphabetic currency codes, normalizes valid lowercase values to uppercase for accounting output, and never truncates, guesses, or replaces invalid currency values. Invalid currency produces `invalid_currency` and no proposed journal. Phase 4 does not yet perform authoritative ISO-4217 validation; practitioner validation remains outstanding.

## Supplier Matching

Supplier matching uses synthetic configurable directory entries. Matching is scoped through the decision request's firm and client context and supports:

- Confident match.
- Candidate matches.
- No match / new supplier flag.

Matching evidence is explainable. Phase 4 does not create or modify supplier bank details.

## Duplicate Detection

Duplicate detection compares the current document and invoice signals against prior succeeded accounting decision runs for the same firm and client. Signals include supplier, invoice number, date, currency, total, and source hash.

Duplicate candidates are warnings with evidence. Phase 4 never deletes, merges, approves, rejects, or suppresses documents automatically.

## Recommendations

Phase 4 persists provider/rule-independent recommendation rows for:

- GL account.
- Tax code.
- Cost centre.
- Category.

Each recommendation stores recommended value, confidence, explanation, evidence, rule name, rule version, optional model version, source document, source extraction run, and timestamps.

The current rule configuration is synthetic. Tax-code recommendations are placeholders marked for review and must not be treated as jurisdiction-specific Malaysian tax advice.

Purchase-invoice recommendations are generated only for supported `purchase_invoice` decision inputs. Unsupported or missing document types receive findings instead of type-specific accounting treatment.

## Proposed Journals

Phase 4 can produce a proposed journal and journal lines for future Phase 5 review. Journal lines include account reference, Decimal debit and credit amounts, optional tax-code and cost-centre references, explanation, and lineage metadata.

Journal balance is validated deterministically:

```text
sum(debits) == sum(credits)
```

An unbalanced proposed journal is explicitly flagged with `unbalanced_journal` and is not represented as valid because of recommendation confidence.

The database invariant ties `total_debits`, `total_credits`, `is_balanced`, and `balance_status` together. The only valid balance states are balanced totals with `is_balanced == true` and `balance_status == balanced`, or unequal totals with `is_balanced == false` and `balance_status == unbalanced`.

## Findings

Implemented stable finding codes include:

- `missing_required_field`
- `unsupported_document_type`
- `invalid_monetary_value`
- `invalid_currency`
- `arithmetic_mismatch`
- `possible_duplicate`
- `new_supplier`
- `low_extraction_confidence`
- `unknown_account_mapping`
- `tax_review_required`
- `unbalanced_journal`

Descriptions are safe human-readable summaries. Audit events do not copy raw invoice payloads or extracted values.

## API

Implemented endpoints:

- `POST /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions`
- `GET /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions`
- `GET /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions/{decision_run_id}`

Execution requires `run_accounting_decision`. Accountant and Senior Reviewer roles receive this permission. Firm Admin, Auditor, and Client Submitter do not.

Viewing uses `review_recommendations` plus tenant/client scope.

## Audit

Phase 4 records:

- `accounting_decision_started`
- `accounting_decision_succeeded`
- `accounting_decision_failed`

Audit metadata is limited to IDs, engine lineage, safe counts, failure code, and balance status. It must not include raw invoice content, extracted values, corrected values, full document payloads, storage keys, credentials, taxpayer identifiers, or bank details.

## Validation Status

**Status: Provisional — requires practitioner validation.**

The accountant interview was postponed. Accounting policy, tax handling, supplier rules, account mappings, duplicate thresholds, and review-routing implications must be validated by practitioners before production use. The Phase 4 architecture is intended to allow those rules to change without redesigning the core decision-run, validation, lineage, and audit model.
