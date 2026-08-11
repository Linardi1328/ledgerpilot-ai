# MVP Scope

## Prototype 1: Invoice-to-Review

Prototype 1 focuses on a synthetic purchase-invoice workflow that turns structured invoice data into a reviewable accounting recommendation.

```text
Synthetic Purchase Invoice
        |
        v
Field Validation
        |
        v
Duplicate Detection
        |
        v
Supplier Matching
        |
        v
Accounting Recommendation
        |
        v
Balanced Journal Suggestion
        |
        v
Confidence & Risk Assessment
        |
        v
Accountant Review
        |
        v
Approve / Correct / Reject / Escalate
        |
        v
Audit History
```

## MVP Objective

Demonstrate a controlled invoice-to-review workflow using synthetic data, deterministic validation, configurable accounting rules, explainable recommendations, and accountant approval.

## Initial MVP Scope

- Synthetic purchase invoices.
- Manual structured input initially.
- Document abstraction.
- Required-field validation.
- Arithmetic validation.
- Duplicate detection.
- Supplier matching.
- Configurable accounting rules.
- General-ledger account recommendations.
- Tax-code recommendation interface.
- Cost-centre recommendation interface.
- Transaction-category recommendations.
- Balanced journal suggestions.
- Confidence information.
- Risk indicators.
- Accountant review.
- Senior escalation.
- Approval.
- Correction.
- Rejection.
- Comments.
- Information requests.
- Audit-event recording.
- Provider-independent future export interface.

## Explicitly Excluded from the Initial MVP

- Real client information.
- Payment execution.
- Supplier-bank-detail changes.
- Autonomous high-risk posting.
- Unsupervised accounting judgement.
- Unsupervised tax advice.
- Full bank reconciliation.
- Real SQL Account integration.
- Production MyInvois integration.
- Custom machine-learning model training.
- Enterprise reporting.
- Payroll.
- Complex frontend.
- Native mobile application.

## Acceptance Boundary

The MVP must be review-oriented. It may recommend, explain, validate, and route work, but it must not post or export accounting entries without human approval and deterministic checks.

## Validation Status

**Status: Provisional — requires practitioner validation.**

The exact approval thresholds, high-risk indicators, chart-of-accounts defaults, tax-code rules, and information-request patterns must be validated with accountants and relevant experts before production use.
