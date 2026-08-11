# Accounting-Control Principles

LedgerPilot AI must preserve accounting integrity and professional judgement.

## AI Trust Boundary

AI output is untrusted input until deterministic validation and human review are complete. AI recommendations cannot bypass required-field checks, arithmetic checks, duplicate detection, approval authority, review routing, or journal-balance rules.

AI must not independently:

- Release payments.
- Change supplier bank details.
- Silently alter approved accounting records.
- Bypass required approval.
- Make complex accounting judgements without human review.
- Provide unsupervised tax advice.
- Provide unsupervised legal advice.
- Hide uncertainty.
- Treat AI-generated output as inherently correct.

## Monetary Precision

All accounting amounts must eventually use decimal arithmetic. Binary floating-point arithmetic must not be used for money, tax, journal totals, balances, or reconciliation amounts.

## Balanced Double Entry

A journal cannot be approved unless:

```text
Total Debits = Total Credits
```

The journal-balance invariant must be deterministic, tested, and independent of any AI provider.

## Traceability

Accounting entries must retain linkage to source evidence, including source document, document version, extracted fields, recommendation, reviewer decision, approval, correction, and audit events.

## Approval Integrity

Approved records cannot be silently rewritten. Changes after approval require controlled workflows that preserve attribution, timing, reason, and previous values.

## Corrections

Corrections must preserve previous values and history. Depending on the accounting impact, future correction workflows should use:

- Correction for pre-export or clerical updates where permitted.
- Reversal for cancelling an approved accounting effect.
- Supersession for replacing an approved record with a corrected successor.

## Recommendation Lineage

Future recommendations should retain:

- Recommendation.
- Explanation.
- Confidence.
- Rule version.
- Model version.
- Reviewer.
- Correction.
- Timestamp.

## Human Review Boundary

Human review is required for exceptions, high-risk transactions, complex judgement, uncertain tax treatment, overrides, and any transaction outside delegated authority.

## Configuration

Accounting rules, approval thresholds, tax-code mappings, chart-of-accounts defaults, supplier-specific rules, and risk indicators must be configurable and versioned.

## Validation Status

**Status: Provisional — requires practitioner validation.**

Accounting policies, tax handling, approval limits, segregation of duties, and correction workflows must be validated with accountants and relevant experts.
