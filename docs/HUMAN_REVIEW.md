# Human Review

## Status

Phase 5 completes the controlled human-review workflow on top of the merged Phase 4
accounting-decision engine.

This implementation records human workflow state and outcomes. It does not turn AI recommendations
into approvals automatically, mutate Phase 4 decisions, post entries, export accounting data, make
payments, change supplier bank details, or integrate with production MyInvois/OCR/auth/storage.

## Review Task and Risk Classification

Each succeeded Phase 4 accounting decision can have one review task. The task preserves:

- firm;
- client;
- document;
- extraction run;
- accounting decision run;
- creator;
- current owner;
- current review state;
- deterministic risk class;
- senior-escalation state and timestamp.

Risk classes are deliberately conservative and synthetic:

- `ordinary`: a balanced proposed journal exists, there are no error findings, and no configured
  senior-routing warning is present;
- `senior_review_required`: a balanced journal exists but a configured material warning such as a
  possible duplicate or low-confidence/unknown mapping requires senior authority;
- `blocked`: deterministic controls found an error, no proposed journal exists, or the proposed
  journal is unbalanced.

`tax_review_required` remains a human-review warning but does not by itself force senior routing in
the synthetic Phase 5 policy. That policy requires practitioner validation before production use.

## Review States

Implemented task states:

- `open`;
- `escalated`;
- `information_requested`;
- `approved`;
- `rejected`.

Terminal states are `approved` and `rejected`.

The persisted escalation state remains either `none` or `senior_review`. State/database constraints
require senior escalation state to carry an escalation timestamp.

## Ownership and RBAC

Review-task creation and modification are tenant/client scoped.

Accountants and senior reviewers can create review tasks. Accountants and senior reviewers can
review, comment, request information, reject, and escalate work when ownership and workflow
preconditions are met.

Ordinary approval requires the assigned accountant or senior reviewer.

A `senior_review_required` task cannot be approved by an accountant. It must be owned by a senior
reviewer in senior-review state, and the approver must have high-risk approval permission.

Auditors remain read-only and can view review tasks/history only inside explicitly authorised client
scope.

Client submitters do not receive internal review access. They can only read the outstanding
information request for an authorised client and submit an information response.

Firm administrators do not gain accounting approval authority through administrative privilege.

## Escalation

Public senior escalation requires:

1. an active `open` task;
2. the current task owner;
3. an active senior reviewer in the same firm;
4. active senior access to the same client; and
5. a non-empty escalation reason.

Escalation transfers ownership to the senior reviewer, records the timestamp, appends the reason as
review history, and emits a safe audit event. The reason text is not copied into audit metadata.

## Comments and Information Requests

Reviewer comments are append-only.

An assigned reviewer can request information from `open` or `escalated` state. The task moves to
`information_requested`.

A client submitter with access to that client can retrieve only the outstanding information-request
text and can submit a response. The response returns the task to:

- `open` when it had not been senior-escalated; or
- `escalated` when senior-review state was already active.

Internal comments and full review history are not exposed through the client information-request
endpoint.

## Approval

Approval is always an explicit human action.

Approval requires:

- current task ownership;
- an active approvable task state;
- no outstanding information request;
- a succeeded source accounting decision;
- deterministic risk classification that still matches the source decision;
- a balanced proposed journal;
- correct ordinary/senior authority; and
- no extraction correction newer than the source accounting decision.

The underlying Phase 4 accounting decision remains unchanged after approval.

An immutable `review_outcome` records the actor, outcome type, exact decision, exact proposed
journal, source-correction count, request correlation identifier, and timestamp.

## Corrected and Approved

Phase 3 extraction corrections are append-only.

When corrections existed before the Phase 4 decision was generated, Phase 4 consumes the latest
effective values. If that decision is subsequently approved, Phase 5 records
`corrected_and_approved`.

When a correction is newer than the reviewed Phase 4 decision, approval fails with
`decision_stale_after_correction`. A fresh accounting decision and review task are required.

This avoids silently approving accounting output that predates the latest corrected evidence.

Direct extraction corrections are rejected with `approved_record_locked` once an approved
review outcome is linked to that extraction. Approval and correction both lock the extraction run
before checking/writing correction state, so a concurrent correction cannot race past approval and a
concurrent approval cannot miss a correction that committed first.

Post-approval correction/reversal/supersession remains a future controlled workflow.

## Rejection

The assigned accountant or senior reviewer may reject an active review task with a required reason.

Rejection creates one immutable `review_outcome`, records an audit event, and makes the task
terminal. A rejected task cannot later be approved or modified.

## Audit History

Phase 5 audit events include:

- `review_task_created`;
- `review_task_escalated`;
- `review_comment_added`;
- `review_information_requested`;
- `review_information_responded`;
- `review_task_approved`;
- `review_task_rejected`.

Audit metadata contains identifiers and workflow state rather than comment bodies, invoice values,
credentials, banking information, or raw accounting payloads.

Authorised review-history responses combine the task, append-only comments, terminal outcome when
present, and scoped audit events.

## API

Existing boundaries:

- `POST .../review-tasks`
- `GET .../review-tasks`
- `GET .../review-tasks/{review_task_id}`

Phase 5 completion adds:

- `POST .../review-tasks/{review_task_id}/escalations`
- `POST .../review-tasks/{review_task_id}/comments`
- `POST .../review-tasks/{review_task_id}/information-requests`
- `GET .../review-tasks/{review_task_id}/information-request`
- `POST .../review-tasks/{review_task_id}/information-responses`
- `POST .../review-tasks/{review_task_id}/approve`
- `POST .../review-tasks/{review_task_id}/reject`
- `GET .../review-tasks/{review_task_id}/history`

All paths are below the existing
`/api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions/{decision_run_id}`
scope.

## Explicitly Out of Scope

Phase 5 does not implement:

- autonomous approval;
- payment execution;
- supplier bank-detail changes;
- accounting posting;
- SQL Account export;
- production MyInvois integration;
- production OCR/auth/storage;
- post-approval reversal or supersession;
- real client/accounting data.

All repository fixtures and examples must remain synthetic.
