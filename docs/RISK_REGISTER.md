# Risk Register

Risk ratings are initial planning estimates and require review as implementation details become known.

| ID | Category | Description | Likelihood | Impact | Rating | Mitigation | Detection | Contingency | Owner | Target phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | Extraction | Incorrect extraction creates wrong invoice fields. | Medium | High | High | Field confidence, validation, human review | Validation failures, reviewer corrections | Manual entry and provider retraining/config changes | Product/Engineering | Phase 3 |
| R-002 | Accounting | Wrong account coding is recommended. | Medium | High | High | Configurable rules, explanations, review | Reviewer corrections, audit analysis | Rule update and senior review | Product/Accounting | Phase 4 |
| R-003 | Tax | Wrong tax recommendation is made. | Medium | High | High | Expert-validated tax configuration, human review | Reviewer corrections, tax review | Disable tax automation until validated | Accounting/Tax expert | Phase 4 |
| R-004 | Accounting | Unbalanced journal is suggested or approved. | Low | High | High | Deterministic balance invariant | Journal-balance tests | Block approval and investigate | Engineering | Phase 4 |
| R-005 | Duplicate | Duplicate document is processed. | Medium | High | High | Duplicate detection and warning | Duplicate reports, reviewer findings | Reverse/supersede and improve rules | Product/Engineering | Phase 4 |
| R-006 | Integration | Duplicate external posting occurs. | Medium | High | High | Idempotency keys and external IDs | Export audit, reconciliation | Reverse external entry and pause export | Engineering | Phase 7 |
| R-007 | Privacy | Cross-client data leakage. | Low | Critical | Critical | Tenant/client isolation and tests | Access logs, tests, reports | Incident response and containment | Security/Engineering | Phase 1 |
| R-008 | Access control | Excessive permissions allow unsafe actions. | Medium | High | High | Least privilege and approval separation | Permission reviews, audit logs | Restrict roles and revoke sessions | Product/Security | Phase 1 |
| R-009 | Secrets | Credential exposure in repo or logs. | Medium | Critical | Critical | Secret management, scans, redaction | Secret scanning, review | Rotate credentials and incident response | Security | Phase 1 |
| R-010 | File security | Malware upload harms systems or users. | Medium | High | High | File allowlist, malware scan, quarantine | Scanner alerts | Quarantine and incident response | Security/Engineering | Phase 2 |
| R-011 | Privacy | Sensitive logs expose financial/personal data. | Medium | High | High | Log redaction and data minimisation | Log review, alerts | Purge logs where possible and notify | Security/Engineering | Phase 1 |
| R-012 | AI | AI hallucination creates false explanation. | Medium | High | High | Treat AI as untrusted; deterministic checks | Reviewer corrections | Disable provider or route to senior review | Product/Engineering | Phase 4 |
| R-013 | Human factors | Users over-rely on confidence scores. | Medium | High | High | Explain uncertainty and require review | Review analytics, training feedback | Adjust UI and training | Product | Phase 5 |
| R-014 | AI | Model drift changes recommendation quality. | Medium | Medium | Medium | Version tracking and monitoring | Correction-rate trends | Revalidate or roll back provider/model | Engineering | Phase 9 |
| R-015 | Rules | Rule drift creates outdated accounting behaviour. | Medium | High | High | Rule versioning and review dates | Rule audits | Disable stale rules or require review | Accounting/Product | Phase 4 |
| R-016 | Integrity | Approved-record mutation hides history. | Low | Critical | Critical | Immutable history, correction/reversal/supersession | Audit checks | Restore from history and investigate | Engineering | Phase 5 |
| R-017 | Governance | Weak separation of duties. | Medium | High | High | Role model and approval thresholds | Permission audits | Reconfigure roles and re-review work | Product/Accounting | Phase 5 |
| R-018 | Availability | Integration outage blocks export. | Medium | Medium | Medium | Queue, retry, status tracking | Export failures | Manual export or delayed retry | Engineering | Phase 7 |
| R-019 | Integration | SQL Account export fails. | Medium | High | High | Gateway abstraction, validation, retries | Export error audit | Manual remediation and retry | Engineering | Phase 7 |
| R-020 | Integration | MyInvois submission fails. | Medium | High | High | Submission status, validation, retry | Submission errors | Manual handling and expert review | Engineering/Tax expert | Phase 8 |
| R-021 | Retention | Retention failure deletes or keeps data improperly. | Medium | High | High | Retention policy and legal review | Retention audits | Restore or securely purge as required | Product/Legal | Phase 10 |
| R-022 | Recovery | Backup failure prevents restoration. | Low | Critical | Critical | Tested backups and recovery runbooks | Restore tests | Disaster recovery process | Engineering | Phase 10 |
| R-023 | Vendor | Vendor lock-in limits provider changes. | Medium | Medium | Medium | Provider-independent boundaries | Architecture review | Add adapter or migrate provider | Engineering | Phase 0+ |
| R-024 | Cost | Provider cost escalation. | Medium | Medium | Medium | Usage monitoring and provider abstraction | Billing alerts | Throttle, switch provider, revise scope | Product/Engineering | Phase 9 |
| R-025 | Data quality | Poor test fixtures hide defects. | Medium | Medium | Medium | Synthetic but realistic fixture design | Test reviews | Improve fixture catalogue | Engineering/Accounting | Phase 1+ |
| R-026 | Advice boundary | Users treat output as professional advice. | Medium | High | High | Clear UI language, approvals, disclaimers | User feedback, audit review | Tighten workflow and training | Product/Legal | Phase 5 |
| R-027 | Delivery | Premature production use. | Medium | Critical | Critical | Production-readiness disclaimers and gates | Deployment review | Disable deployment and communicate limits | Owner/Product | Phase 0+ |

## Notes

- Owners are planning owners, not assigned staff.
- Likelihood and impact must be revisited after accountant interviews and technical discovery.
