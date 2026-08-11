# Role and Permission Model

## Roles

### Firm Administrator

Purpose: manages the workspace, users, role assignment, configuration, and integration settings.

Administrative access must not automatically bypass accounting controls.

Typical responsibilities:

- Workspace administration.
- User administration.
- Role assignment.
- Configuration.
- Integration configuration.

### Accountant

Purpose: performs ordinary accounting review and correction within delegated authority.

Typical responsibilities:

- Review documents.
- Correct extracted information.
- Review coding.
- Approve ordinary transactions within authority.
- Reject transactions.
- Request information.
- Perform reconciliation work.

### Senior Reviewer

Purpose: reviews and approves unusual, high-risk, high-value, sensitive, or overridden transactions.

Typical responsibilities:

- Review unusual transactions.
- Review high-risk transactions.
- Review high-value transactions.
- Resolve exceptions.
- Approve sensitive entries.
- Review overrides.

### Client / Document Submitter

Purpose: submits supporting documents and responds to information requests for authorised client entities.

Typical responsibilities:

- Upload supporting documents.
- Respond to information requests.
- View authorised status.

This role must not access other clients.

### Auditor / Read-Only User

Purpose: reviews evidence and history without modifying records.

Typical responsibilities:

- View evidence.
- View recommendations.
- View journals.
- View approvals.
- View corrections.
- View audit history.

This role cannot modify records.

## Permission Matrix

Legend:

- Yes: allowed when tenant/client scope and preconditions are satisfied.
- Limited: allowed only under configured authority, assignment, or workflow rules.
- No: not allowed.

| Permission | Firm Administrator | Accountant | Senior Reviewer | Client / Document Submitter | Auditor / Read-Only User |
| --- | --- | --- | --- | --- | --- |
| Upload documents | Limited | Yes | Yes | Yes, own authorised client only | No |
| View documents | Limited | Yes, assigned/authorised clients | Yes, assigned/authorised clients | Limited, own submitted/authorised documents | Yes, authorised scope only |
| Correct extracted information | No | Yes, before approval | Yes, before approval or during correction workflow | No | No |
| Review recommendations | Limited | Yes | Yes | No | Yes |
| Approve ordinary transaction | No by default | Limited | Yes | No | No |
| Approve high-risk transaction | No by default | No | Limited | No | No |
| Reject | No by default | Yes | Yes | No | No |
| Escalate | Limited | Yes | Yes | No | No |
| Request information | Limited | Yes | Yes | No | No |
| View audit history | Limited | Yes, authorised scope | Yes, authorised scope | Limited, own authorised scope | Yes, authorised scope |
| Manage users | Yes | No | No | No | No |
| Manage configuration | Yes | No | Limited review input only | No | No |
| Manage integrations | Yes | No | No | No | No |
| Export approved entries | Limited, operational only | Limited | Limited | No | No |
| Correct approved records | No direct overwrite | Controlled correction request | Controlled correction/reversal/supersession | No | No |

No user role may silently overwrite an approved accounting record.

## Control Principles

- Administrative privilege is separated from accounting approval authority.
- Role assignment must be auditable.
- Permissions are tenant-scoped and client-scoped.
- Approval authority must be configurable.
- High-risk work must be routed to senior review.
- Auditors are read-only.
- Client users can only access authorised client records.
- Corrections after approval require attributable history.

## Open Validation Questions

- What transaction values require senior review?
- Which ordinary transaction types may accountants approve without second review?
- Which clients require stricter segregation of duties?
- Which overrides require mandatory comment and senior approval?

**Status: Provisional — requires practitioner validation.**
