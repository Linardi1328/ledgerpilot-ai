# MVP Acceptance Criteria

These criteria describe measurable future MVP behaviour. They are not implemented in Phase 0.

| ID | Acceptance criterion | Evidence expected |
| --- | --- | --- |
| AC-001 | A journal cannot be approved if total debits and total credits differ. | Journal-balance tests. |
| AC-002 | Failed extraction cannot lead to approval. | Workflow-state tests. |
| AC-003 | Missing required invoice fields block recommendation or approval until corrected or information is supplied. | Field-validation tests. |
| AC-004 | Arithmetic mismatches between invoice lines, tax, subtotal, and total are flagged and block approval. | Arithmetic-validation tests. |
| AC-005 | Duplicate warnings include an explanation reviewers can inspect. | Duplicate-detection tests and reviewer evidence. |
| AC-006 | High-risk transactions can require senior review. | Routing tests. |
| AC-007 | Approved records cannot be silently overwritten. | Persistence and mutation tests. |
| AC-008 | Corrections produce attributable history. | Correction audit tests. |
| AC-009 | Approval records actor, timestamp, tenant/client scope, target record, and decision. | Audit-event tests. |
| AC-010 | Rule and model versions are traceable from recommendation to review decision. | Recommendation-lineage tests. |
| AC-011 | Retry operations must not duplicate external exports. | Idempotency tests. |
| AC-012 | Firm A cannot retrieve Firm B data through authorised application paths. | Tenant-isolation tests. |
| AC-013 | Client users cannot access other clients. | Client-isolation tests. |
| AC-014 | Development fixtures contain synthetic data only. | Fixture review and sensitive-data scan. |
| AC-015 | AI confidence is displayed as uncertainty, not proof of correctness. | Reviewer workflow tests. |
| AC-016 | Tax-code recommendations are labelled as reviewable recommendations and cannot be treated as unsupervised tax advice. | Review workflow and content tests. |
| AC-017 | Information requests record requester, recipient, question, status, response, and timestamp. | Information-request tests. |
| AC-018 | Rejected work records a reason and cannot be exported. | Rejection workflow tests. |
| AC-019 | Senior-review overrides require reason and attribution. | Override tests. |
| AC-020 | Public repository examples, tests, and documentation do not include real client, bank, taxpayer, employee, or credential data. | Pre-push safety review. |

## Validation Status

**Status: Provisional — requires practitioner validation.**
