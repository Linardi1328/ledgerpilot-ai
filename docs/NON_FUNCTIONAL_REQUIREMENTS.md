# Non-Functional Requirements

Non-functional requirements define quality attributes and constraints. Phase 4 implements selected infrastructure, intake, extraction, and accounting decision controls while production hardening remains future work.

| ID | Area | Requirement | Priority | Evidence expected in future phases | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Security | Enforce authentication, authorisation, least privilege, tenant isolation, and secure secret handling. | Must | Security tests, access-control tests, deployment review | Provisional |
| NFR-002 | Privacy | Minimise sensitive data collection and prevent unnecessary exposure in logs, fixtures, exports, and support workflows. | Must | Privacy review, log-redaction tests | Requires legal/privacy assessment |
| NFR-003 | Tenant isolation | Firm and client data must be isolated across application paths, storage, exports, logs, and audit views. | Must | Cross-tenant and cross-client tests | Provisional |
| NFR-004 | Accounting integrity | Accounting invariants must be deterministic and independent of AI/provider output. | Must | Unit and integration tests | Provisional |
| NFR-005 | Auditability | Material events must be attributable, timestamped, scoped, and reviewable. | Must | Audit-event tests | Provisional |
| NFR-006 | Reliability | Workflow steps should fail safely and not create duplicate accounting effects. | Must | Failure-mode tests | Requires technical investigation |
| NFR-007 | Recoverability | Data and document storage must be recoverable from tested backups before production use. | Must | Restore tests, recovery runbooks | Requires technical investigation |
| NFR-008 | Performance | Review workflows should remain responsive for expected firm workloads without unsupported guarantees. | Should | Load tests after usage targets are known | Requires practitioner validation |
| NFR-009 | Scalability | The modular monolith should support incremental scaling before any service split is considered. | Should | Profiling and capacity tests | Requires technical investigation |
| NFR-010 | Accessibility | User interfaces should be usable with keyboard navigation, readable contrast, and assistive technology support. | Should | Accessibility checks | Provisional |
| NFR-011 | Maintainability | Code should follow clear module boundaries, typed interfaces, tests, and documentation. | Must | Ruff, Mypy, tests, review | Provisional |
| NFR-012 | Testability | Accounting rules, validation, routing, and provider boundaries must be testable without real external providers. | Must | Unit tests and fakes | Provisional |
| NFR-013 | Observability | Logs, metrics, traces, and audit events should support diagnosis without leaking sensitive data. | Should | Observability review and redaction tests | Requires technical investigation |
| NFR-014 | Explainability | Recommendations, duplicate warnings, risk indicators, and review routing should be explainable to reviewers. | Must | Explanation fields and tests | Requires practitioner validation |
| NFR-015 | Provider independence | Core accounting logic must not permanently depend on a commercial AI, OCR, storage, MyInvois, or accounting-platform provider. | Must | Interface tests and architecture review | Provisional |
| NFR-016 | Portability | Local development should use standard Python tooling and portable configuration. | Should | Fresh-clone setup check | Provisional |
| NFR-017 | Configuration | Accounting rules, thresholds, tax mappings, cost centres, providers, and approval policies should be configurable and versioned. | Must | Configuration/version tests | Requires practitioner validation |
| NFR-018 | Data retention | Retention and deletion should be configurable and aligned with legal, tax, accounting, and contractual duties. | Must | Retention tests and legal review | Requires legal/privacy assessment |
| NFR-019 | Error handling | Errors should be actionable, non-leaky, attributable, and safe to retry where appropriate. | Must | Error-path tests | Provisional |
| NFR-020 | Idempotency | External exports and submissions must avoid duplicate external effects during retries. | Must | Idempotency tests | Requires technical investigation |
| NFR-021 | Concurrency | Simultaneous review and correction actions must preserve consistency and avoid lost updates. | Must | Concurrency tests | Requires technical investigation |
| NFR-022 | Decimal precision | Monetary calculations must use decimal arithmetic, not binary floating point. | Must | Money-type tests and static review | Confirmed |
| NFR-023 | Time-zone handling | Timestamps must be stored consistently and displayed appropriately for firm/client context. | Should | Time-zone tests | Requires practitioner validation |
| NFR-024 | Version tracking | Rule versions, model versions, document versions, recommendation versions, and export attempts must be retained where relevant. | Must | Version-lineage tests | Provisional |

## Constraint

No Phase 0 document should be read as a production-readiness claim.
