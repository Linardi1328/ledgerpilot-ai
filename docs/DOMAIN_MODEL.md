# Conceptual Domain Model

This model is conceptual only. Phase 0 does not implement database tables.

## Domain Diagram

```mermaid
erDiagram
    Firm ||--o{ FirmUser : has
    Firm ||--o{ ClientEntity : serves
    FirmUser }o--o{ Role : assigned
    Role }o--o{ Permission : grants
    ClientEntity ||--o{ Document : owns
    Document ||--o{ DocumentVersion : versions
    DocumentVersion ||--o{ DocumentFile : stores
    Document ||--o{ ExtractionRun : has
    ExtractionRun ||--o{ ExtractedField : produces
    Supplier ||--o{ Invoice : issues
    Customer ||--o{ Invoice : receives
    Invoice ||--o{ InvoiceLine : contains
    Invoice ||--o{ TaxComponent : includes
    ChartOfAccounts ||--o{ GeneralLedgerAccount : contains
    AccountingRule ||--o{ Recommendation : produces
    Recommendation ||--o{ Journal : suggests
    Journal ||--o{ JournalLine : contains
    ReviewTask ||--o{ Approval : may_result_in
    ReviewTask ||--o{ Rejection : may_result_in
    ReviewTask ||--o{ Correction : may_result_in
    ReviewTask ||--o{ Comment : includes
    ReviewTask ||--o{ InformationRequest : includes
    Journal ||--o{ IntegrationExport : exported_by
    Document ||--o{ AuditEvent : records
    Recommendation ||--o{ AuditEvent : records
    Journal ||--o{ AuditEvent : records
```

## Concepts

| Concept | Purpose | Relationships and tenant ownership | Mutability and lifecycle | Audit implications |
| --- | --- | --- | --- | --- |
| Firm | Accounting firm tenant. | Owns firm users, clients, configuration, rules, integrations, and audit scope. | Mutable administrative metadata; lifecycle from active to suspended/closed. | Firm-level configuration and access changes are auditable. |
| FirmUser | Person operating inside a firm tenant. | Belongs to firm; assigned roles and client scopes. | Mutable profile and access status. | Role, permission, and status changes are auditable. |
| Role | Named access bundle. | Assigned to firm users; grants permissions. | Configurable but versioned or audited. | Role changes affect control environment and require audit history. |
| Permission | Atomic capability. | Granted through roles and checked against tenant/client scope. | Usually stable; additions require review. | Permission evaluation failures and grants may be security-relevant. |
| ClientEntity | Client organisation or business represented by the firm. | Owned by firm; owns documents, invoices, suppliers, customers, journals. | Mutable metadata; lifecycle active/inactive/archived. | Client access and data changes must be auditable. |
| ClientUser | External submitter or authorised viewer. | Belongs to client scope and may authenticate separately. | Mutable access status and contact details. | Access grants, uploads, and responses are auditable. |
| Document | Logical supporting document. | Owned by client entity; linked to versions, files, extraction, invoice, review. | State-driven; not silently overwritten. | State transitions and associations are auditable. |
| DocumentVersion | Version of document metadata/content interpretation. | Belongs to document; linked to file and extraction runs. | Append/supersede rather than overwrite. | Version creation and supersession require audit events. |
| DocumentFile | Stored original or derivative file reference. | Belongs to document version and storage provider. | Immutable file reference where possible; archived by policy. | Access and retention actions may be audited. |
| DocumentClassification | Document type/classification result. | Linked to document or extraction run. | May be corrected with history. | Classification source, confidence, and correction should be retained. |
| ExtractionRun | Attempt to extract data. | Belongs to document version; references provider/model. | Immutable run record after completion. | Provider, version, status, errors, and outputs are auditable. |
| ExtractedField | Extracted value for a document field. | Belongs to extraction run; may map to invoice fields. | Original extraction immutable; reviewed values use correction. | Field source and corrections are traceable. |
| FieldConfidence | Confidence score or assessment for a field. | Belongs to extracted field. | Immutable per extraction run. | Supports uncertainty review and model monitoring. |
| Supplier | Counterparty supplying goods/services. | Owned by client entity; linked to identifiers, invoices, rules. | Mutable through controlled changes; bank changes are high risk and out of MVP. | Supplier changes and matches are auditable. |
| Customer | Counterparty receiving goods/services. | Owned by client entity; linked to identifiers and invoices. | Mutable through controlled changes. | Customer changes and matches are auditable. |
| BusinessIdentifier | Registration, tax, or other identifier. | Belongs to supplier, customer, firm, or client. | Mutable with history; validated status may change. | Identifier validation and changes are auditable. |
| Invoice | Structured invoice representation. | Belongs to client entity and document; linked to lines, tax, supplier/customer, journal. | Draft until approved; later changes require correction/supersession. | Invoice field changes and approval decisions are auditable. |
| InvoiceLine | Line item on invoice. | Belongs to invoice; may link to GL recommendations. | Mutable before approval; later through correction workflow. | Line corrections affect accounting history. |
| TaxComponent | Tax amount/rate/code detail. | Belongs to invoice or invoice line; linked to tax code. | Requires expert-validated rules; mutable before approval. | Tax recommendations and corrections require traceability. |
| Currency | Currency code and precision. | Referenced by invoice, journal, bank transaction. | Reference data; rarely changes. | Currency changes can affect money interpretation and should be controlled. |
| ChartOfAccounts | Account catalogue for client or firm template. | Owned by client entity or firm template; contains GL accounts. | Configurable and versioned. | Account changes impact recommendations and exports. |
| GeneralLedgerAccount | Posting account. | Belongs to chart of accounts; used by journal lines and rules. | Mutable metadata; historical postings retain account reference/version. | Account mapping changes are auditable. |
| TaxCode | Tax classification/code. | Owned by client/firm configuration; referenced by recommendations and journals. | Configurable and versioned; requires expert validation. | Tax-code changes and use are auditable. |
| CostCentre | Optional reporting dimension. | Owned by client entity; referenced by recommendations/journal lines. | Mutable before approval; historical use retained. | Changes affect reporting lineage. |
| Department | Optional organisation dimension. | Owned by client entity; referenced by rules or journal lines. | Configurable lifecycle. | Changes are auditable where used in postings. |
| Project | Optional project/job dimension. | Owned by client entity; referenced by rules or journal lines. | Configurable lifecycle. | Changes are auditable where used in postings. |
| AccountingRule | Configurable rule for coding/routing. | Owned by firm/client; produces recommendations. | Versioned; changes do not rewrite prior recommendations. | Rule versions are part of recommendation lineage. |
| SupplierSpecificRule | Rule scoped to supplier. | Owned by client and supplier. | Versioned and reviewed. | Supplier-specific coding changes are auditable. |
| Recommendation | Suggested accounting treatment. | Linked to invoice, rules, models, confidence, risk, journal. | Immutable once issued; superseded by new recommendation. | Explanation, confidence, versions, and reviewer action retained. |
| RecommendationExplanation | Human-readable reason. | Belongs to recommendation. | Immutable with recommendation. | Supports review, training, and dispute analysis. |
| RecommendationConfidence | Confidence or uncertainty indicator. | Belongs to recommendation. | Immutable with recommendation. | Must not be treated as proof of correctness. |
| RiskIndicator | Flag such as duplicate, high value, unusual supplier, low confidence. | Linked to document, invoice, recommendation, or review task. | Immutable per assessment; new assessment can supersede. | Risk routing and override decisions are auditable. |
| Journal | Draft or approved accounting entry. | Linked to invoice, recommendation, approval, export. | Draft mutable; approved immutable except correction/reversal/supersession. | Journal approval and correction are core audit events. |
| JournalLine | Debit or credit line. | Belongs to journal; references GL account, tax code, dimensions. | Mutable before approval; immutable after approval. | Amount/account changes require traceability. |
| ReviewTask | Work item for accountant/senior reviewer. | Linked to document/invoice/recommendation/journal. | State-driven assignment and completion. | Assignment, escalation, and outcome are auditable. |
| Approval | Decision accepting work. | Linked to review task and approved journal. | Immutable decision record. | Actor, time, authority, and scope required. |
| Rejection | Decision rejecting work. | Linked to review task/document/invoice. | Immutable decision record. | Reason and actor required. |
| Correction | Attributable change to extracted/accounting data. | Linked to prior value, new value, reviewer, and target record. | Immutable correction record; may produce new version. | Preserves history and supports review. |
| Comment | Reviewer or submitter note. | Linked to review task, document, or information request. | Mutable only under controlled edit policy; preferably append-only. | Comments may support approval rationale and must avoid secrets. |
| InformationRequest | Request for missing/unclear information. | Linked to review task and submitter/client. | State-driven open/responded/closed/cancelled. | Requests and responses are auditable. |
| BankTransaction | Future bank feed/import item. | Owned by client entity; linked to reconciliation matches. | Imported immutable; enrichment uses versions/corrections. | Reconciliation and changes are auditable. |
| ReconciliationMatch | Candidate or approved match between bank transaction and accounting records. | Owned by client entity; linked to reviewer. | Candidate mutable; approved immutable. | Match decisions and reversals are auditable. |
| IntegrationExport | Export attempt to accounting platform. | Linked to approved journal and provider gateway. | Immutable attempt record with retry/status updates. | Idempotency keys, external IDs, errors, and actor/system are auditable. |
| MyInvoisSubmission | Future e-Invoice submission record. | Linked to invoice/client and MyInvois provider. | State-driven; updates retain external status history. | Validation, rejection, cancellation, IDs, and retries are auditable. |
| AuditEvent | Attributable event record. | Scoped to firm/client and target entity. | Append-only. | Core evidence source for review and audit. |
| RuleVersion | Specific version of accounting/routing/tax rule. | Linked to recommendations and decisions. | Immutable once active/used. | Enables explanation and rollback analysis. |
| ModelVersion | Specific AI/OCR/model/provider version. | Linked to extraction and recommendation outputs. | Immutable reference. | Enables drift, quality, and accountability review. |

## Open Modelling Questions

- Which entities must be firm-level templates versus client-level configuration?
- What is the minimum required audit-event schema?
- How should document versions relate to corrected structured data?
- Which supplier/customer identifiers are required in Malaysia for MVP and future MyInvois?

**Status: Provisional — requires practitioner and technical validation.**
