# Roadmap

The roadmap is provisional and must adapt to practitioner interviews, technical discovery, and independent review. Future phases are not complete.

## 1. Repository Bootstrap

Objective: establish the public GitHub repository baseline.

Deliverables:

- Minimal `.gitignore`.
- Minimal `README.md`.
- Minimal `PROJECT_HANDOVER.md`.
- Initial `main` branch push.

Exit criteria:

- Repository has an initial commit on `main`.
- Remote `main` exists.

Risks:

- Accidentally committing non-bootstrap work directly to `main`.

Dependencies:

- GitHub repository and local clone.

## 2. Phase 0: Foundation and Discovery

Objective: document the product foundation, controls, architecture direction, and minimal tooling.

Deliverables:

- Charter, MVP, requirements, NFRs, acceptance criteria.
- Roles, permissions, workflows, state models, domain model.
- Accounting principles, security, privacy, risk register.
- Architecture direction, provider boundaries, SQL Account/MyInvois direction.
- ADRs, README, contribution workflow, AI-development rules.
- Minimal Python package, Pytest, Ruff, Mypy configuration.

Exit criteria:

- Verification commands run and results reported.
- Sensitive-data review completed.
- Review branch pushed.
- Pull request opened into `main`.
- Independent review requested.

Risks:

- Overstating implementation status.
- Missing practitioner-validation markers.
- Including real data or secrets.

Dependencies:

- Repository bootstrap.

## 3. Phase 1: Core Infrastructure

Objective: establish secure backend foundations without business automation.

Deliverables:

- FastAPI application skeleton.
- Configuration management.
- Database setup and migrations.
- Authentication and RBAC foundations.
- Tenant/client ownership primitives.
- Audit-event infrastructure.

Exit criteria:

- Core app runs locally.
- Access-control and tenant-isolation tests exist.
- No accounting automation claims yet.

Risks:

- Weak tenant isolation.
- Premature feature work.
- Poor migration discipline.

Dependencies:

- Phase 0 approval.

## 4. Phase 2: Secure Document Intake

Objective: accept and store synthetic supporting documents safely.

Deliverables:

- Document metadata model.
- File validation.
- File-type allowlist.
- File-size limits.
- Malware scanning design/integration.
- Quarantine workflow.
- Controlled storage references.

Exit criteria:

- Invalid files are rejected or quarantined.
- Original-file traceability exists.
- Uploads remain tenant/client scoped.

Risks:

- Malware handling gaps.
- Sensitive-file leakage.
- Storage access mistakes.

Dependencies:

- Phase 1 identity, tenant, storage, audit foundations.

## 5. Phase 3: OCR and Extraction

Objective: extract structured fields from synthetic documents through provider-independent boundaries.

Deliverables:

- OCR/extraction provider interface.
- Extraction run records.
- Extracted fields and confidence.
- Manual correction path.
- Synthetic fixtures.

Exit criteria:

- Extraction failures cannot proceed to approval.
- Field confidence and provider version are retained.

Risks:

- Provider lock-in.
- Low-quality extraction.
- Over-trusting confidence.

Dependencies:

- Phase 2 secure document intake.

## 6. Phase 4: Accounting Decision Engine

Objective: recommend accounting treatment using deterministic rules and reviewable provider-independent recommendations.

Deliverables:

- Required-field validation.
- Arithmetic validation.
- Duplicate detection.
- Supplier/customer matching.
- Configurable accounting rules.
- GL, tax-code, cost-centre, and category recommendation interfaces.
- Balanced journal suggestions.

Exit criteria:

- Journals cannot be approved unless balanced.
- Recommendations include explanation, confidence, and rule/model lineage.

Risks:

- Wrong coding or tax recommendation.
- Rule drift.
- Unbalanced journals.

Dependencies:

- Phase 3 extraction and correction foundations.
- Practitioner validation.

## 7. Phase 5: Human Review

Objective: implement accountant review, senior escalation, approval, rejection, correction, comments, information requests, and audit history.

Deliverables:

- Review-task lifecycle.
- Approval authority checks.
- Senior-review routing.
- Controlled correction before approval.
- Audit history views.

Exit criteria:

- High-risk work routes to senior review.
- Approved records cannot be silently overwritten.
- Corrections produce history.

Risks:

- Weak separation of duties.
- Approval bypass.
- Users treating recommendations as advice.

Dependencies:

- Phase 4 accounting decision engine.

## 8. Phase 6: Bank Reconciliation

Objective: support controlled bank-transaction matching workflows.

Deliverables:

- Bank transaction import abstraction.
- Candidate match suggestions.
- Review and approval workflow.
- Reconciliation audit history.

Exit criteria:

- Reconciliation matches require review.
- Unmatched and disputed transactions are visible.

Risks:

- Duplicate matches.
- Incorrect bank data handling.
- Scope expansion beyond MVP.

Dependencies:

- Phase 5 review infrastructure.

## 9. Phase 7: Accounting Integrations / SQL Account

Objective: export approved accounting entries through provider-independent accounting-platform gateways, starting with SQL Account direction.

Deliverables:

- AccountingPlatformGateway interface.
- SQLAccountGateway adapter.
- Account/supplier/customer/tax-code retrieval where supported.
- Purchase invoice and journal export.
- Idempotency, retry, duplicate prevention, error recovery, audit history.

Exit criteria:

- Retry does not duplicate external postings.
- Only approved entries can export.
- External IDs and errors are retained.

Risks:

- SQL Account API constraints.
- Export failures.
- Duplicate external posting.

Dependencies:

- Phase 5 approvals.
- SQL Account technical investigation.

## 10. Phase 8: Malaysian MyInvois

Objective: support future Malaysian e-Invoice workflows after expert validation.

Deliverables:

- MyInvois/e-Invoice provider boundary.
- Submission, validation, rejection, cancellation, and status tracking.
- Validated identifier handling.
- Integration audit history.

Exit criteria:

- MyInvois requirements are independently verified.
- Submission status and errors are auditable.

Risks:

- Regulatory misunderstanding.
- Taxpayer identifier mishandling.
- Production integration failure.

Dependencies:

- Phase 7 integration patterns.
- Malaysian tax/accounting/privacy validation.

## 11. Phase 9: Analytics and ML

Objective: improve quality monitoring and optional learning workflows without weakening controls.

Deliverables:

- Recommendation quality metrics.
- Correction analytics.
- Model/rule drift monitoring.
- Optional ML experiments using synthetic or authorised data only.

Exit criteria:

- Analytics do not expose sensitive data.
- Model changes are versioned and reviewable.

Risks:

- Model drift.
- Cost escalation.
- Privacy overreach.

Dependencies:

- Sufficient reviewed workflow data and privacy/legal approval.

## 12. Phase 10: Production Hardening

Objective: prepare for controlled production readiness.

Deliverables:

- Security review.
- Privacy/legal review.
- Backup and restore tests.
- Disaster recovery plan.
- Incident response process.
- Dependency/security scanning.
- Performance and reliability testing.

Exit criteria:

- Production controls are tested and documented.
- Residual risks are accepted by owner.

Risks:

- Premature production use.
- Untested recovery.
- Incomplete legal/privacy obligations.

Dependencies:

- Prior product phases and independent reviews.

## 13. Future Accounting Firm Pilot

Objective: validate LedgerPilot AI with a controlled accounting-firm pilot.

Deliverables:

- Pilot plan.
- Synthetic or explicitly authorised data handling rules.
- User training.
- Feedback process.
- Support and rollback plan.

Exit criteria:

- Pilot success criteria met.
- Issues triaged.
- Owner decides next rollout step.

Risks:

- Users misunderstand AI boundary.
- Real data handled before controls are production-ready.
- Pilot feedback changes core assumptions.

Dependencies:

- Production readiness approval.
- Firm participation and agreements.
