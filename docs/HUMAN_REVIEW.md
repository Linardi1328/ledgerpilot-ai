# Human Review

## Status

Phase 5 begins with a deliberately narrow human-review foundation built on the merged Phase 4 accounting-decision engine.

This slice creates controlled review tasks for succeeded accounting decision runs. It does not create accounting approvals, postings, exports, payment instructions, supplier bank-detail changes, MyInvois submissions, or autonomous accounting decisions.

## Implemented Boundary

A succeeded Phase 4 accounting decision can have one review task. The task retains firm, client, document, extraction-run, and decision-run identifiers so source evidence and decision lineage remain explicit.

Review tasks have only two states in this slice:

- `open` with escalation state `none` and no escalation timestamp;
- `escalated` with escalation state `senior_review` and an escalation timestamp.

The only allowed lifecycle transition is `open -> escalated`. Completion, approval, correction, rejection, information requests, comments, and posting are intentionally deferred.

## Ownership and RBAC

Only `accountant` and `senior_reviewer` principals can use the review-task create/read API boundaries.

A task owner must:

- be an active firm membership;
- have the `accountant` or `senior_reviewer` role;
- have active access to the task client.

Persistence also links task ownership to the owner membership's client-access record and links every task to the exact Phase 4 decision scope. These constraints prevent a task from being attached to a different tenant/client/document/extraction decision tuple.

## Escalation

The service supports one deterministic escalation operation for this slice. Escalation:

1. requires an existing `open` task;
2. requires a client-authorized `senior_reviewer` target;
3. changes status to `escalated`;
4. changes escalation state to `senior_review`;
5. records the escalation timestamp;
6. transfers review ownership to the senior reviewer; and
7. appends a `review_task_escalated` audit event.

The public API remains read/create only in this first slice. A public mutation boundary for escalation is intentionally deferred until the next human-review slice.

## Audit History

Task creation appends `review_task_created`. Senior escalation appends `review_task_escalated`. Audit metadata contains identifiers and workflow state only; it does not copy invoice values, credentials, bank details, or other accounting payload data.

Audit events do not imply approval. A Phase 4 recommendation remains a recommendation after review-task creation or escalation.

## API

Implemented endpoints:

- `POST /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions/{decision_run_id}/review-tasks`
- `GET /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions/{decision_run_id}/review-tasks`
- `GET /api/v1/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}/accounting-decisions/{decision_run_id}/review-tasks/{review_task_id}`

The create request may include `owner_membership_id`. If omitted, ownership defaults to the current reviewer membership.

## Explicitly Out of Scope

This slice does not implement:

- approval or rejection outcomes;
- automatic approval from AI confidence or recommendations;
- correction of approved records;
- payment execution;
- supplier bank-detail changes;
- SQL Account export;
- production MyInvois integration;
- production OCR, authentication, or storage;
- real client/accounting data.

All test fixtures and examples remain synthetic.
