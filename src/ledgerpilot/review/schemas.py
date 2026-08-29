from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ledgerpilot.persistence.models.audit import AuditEvent
from ledgerpilot.persistence.models.review import ReviewComment, ReviewOutcome, ReviewTask


class ReviewTaskCreateRequest(BaseModel):
    owner_membership_id: UUID | None = None


class ReviewEscalationRequest(BaseModel):
    senior_membership_id: UUID
    reason: str = Field(min_length=1, max_length=2000)


class ReviewCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ReviewInformationRequestCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ReviewInformationResponseCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ReviewApprovalRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ReviewRejectionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ReviewTaskResponse(BaseModel):
    id: UUID
    firm_id: UUID
    client_id: UUID
    decision_run_id: UUID
    document_id: UUID
    extraction_run_id: UUID
    created_by_user_id: UUID
    created_by_membership_id: UUID
    owner_user_id: UUID
    owner_membership_id: UUID
    status: str
    risk_class: str
    escalation_state: str
    escalated_at: datetime | None
    request_id: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: ReviewTask) -> ReviewTaskResponse:
        return cls(
            id=task.id,
            firm_id=task.firm_id,
            client_id=task.client_id,
            decision_run_id=task.decision_run_id,
            document_id=task.document_id,
            extraction_run_id=task.extraction_run_id,
            created_by_user_id=task.created_by_user_id,
            created_by_membership_id=task.created_by_membership_id,
            owner_user_id=task.owner_user_id,
            owner_membership_id=task.owner_membership_id,
            status=task.status,
            risk_class=task.risk_class,
            escalation_state=task.escalation_state,
            escalated_at=task.escalated_at,
            request_id=task.request_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class ReviewCommentResponse(BaseModel):
    id: UUID
    review_task_id: UUID
    author_user_id: UUID
    author_membership_id: UUID
    kind: str
    body: str
    request_id: str | None
    created_at: datetime

    @classmethod
    def from_comment(cls, comment: ReviewComment) -> ReviewCommentResponse:
        return cls(
            id=comment.id,
            review_task_id=comment.review_task_id,
            author_user_id=comment.author_user_id,
            author_membership_id=comment.author_membership_id,
            kind=comment.kind,
            body=comment.body,
            request_id=comment.request_id,
            created_at=comment.created_at,
        )


class ReviewOutcomeResponse(BaseModel):
    id: UUID
    review_task_id: UUID
    actor_user_id: UUID
    actor_membership_id: UUID
    outcome_type: str
    proposed_journal_id: UUID | None
    source_correction_count: int
    reason: str | None
    request_id: str | None
    created_at: datetime

    @classmethod
    def from_outcome(cls, outcome: ReviewOutcome) -> ReviewOutcomeResponse:
        return cls(
            id=outcome.id,
            review_task_id=outcome.review_task_id,
            actor_user_id=outcome.actor_user_id,
            actor_membership_id=outcome.actor_membership_id,
            outcome_type=outcome.outcome_type,
            proposed_journal_id=outcome.proposed_journal_id,
            source_correction_count=outcome.source_correction_count,
            reason=outcome.reason,
            request_id=outcome.request_id,
            created_at=outcome.created_at,
        )


class ReviewAuditEventResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    event_type: str
    target_type: str
    target_id: str
    occurred_at: datetime
    request_id: str | None
    metadata: dict[str, Any]

    @classmethod
    def from_event(cls, event: AuditEvent) -> ReviewAuditEventResponse:
        return cls(
            id=event.id,
            actor_user_id=event.actor_user_id,
            event_type=event.event_type,
            target_type=event.target_type,
            target_id=event.target_id,
            occurred_at=event.occurred_at,
            request_id=event.request_id,
            metadata=event.metadata_json,
        )


class ReviewInteractionResponse(BaseModel):
    task: ReviewTaskResponse
    comment: ReviewCommentResponse


class ReviewResolutionResponse(BaseModel):
    task: ReviewTaskResponse
    outcome: ReviewOutcomeResponse


class ReviewHistoryResponse(BaseModel):
    task: ReviewTaskResponse
    comments: list[ReviewCommentResponse]
    outcome: ReviewOutcomeResponse | None
    audit_events: list[ReviewAuditEventResponse]
