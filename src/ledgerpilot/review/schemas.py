from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ledgerpilot.persistence.models.review import ReviewTask


class ReviewTaskCreateRequest(BaseModel):
    owner_membership_id: UUID | None = None


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
            escalation_state=task.escalation_state,
            escalated_at=task.escalated_at,
            request_id=task.request_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
