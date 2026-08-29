from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ledgerpilot.persistence.models.reconciliation_review import (
    ReconciliationOutcomeRecord,
    ReconciliationReviewActionRecord,
    ReconciliationReviewRecord,
)


class ReconciliationReviewCreateRequest(BaseModel):
    match_run_id: UUID


class ReconciliationCandidateSelectionRequest(BaseModel):
    review_outcome_id: UUID


class ReconciliationReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ReconciliationApprovalRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ReconciliationReviewResponse(BaseModel):
    id: UUID
    bank_transaction_id: UUID
    match_run_id: UUID
    created_by_user_id: UUID
    created_by_membership_id: UUID
    status: str
    selected_review_outcome_id: UUID | None
    request_id: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: ReconciliationReviewRecord) -> ReconciliationReviewResponse:
        return cls(
            id=record.id,
            bank_transaction_id=record.bank_transaction_id,
            match_run_id=record.match_run_id,
            created_by_user_id=record.created_by_user_id,
            created_by_membership_id=record.created_by_membership_id,
            status=record.status,
            selected_review_outcome_id=record.selected_review_outcome_id,
            request_id=record.request_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class ReconciliationReviewActionResponse(BaseModel):
    id: UUID
    reconciliation_review_id: UUID
    bank_transaction_id: UUID
    match_run_id: UUID
    actor_user_id: UUID
    actor_membership_id: UUID
    action_type: str
    candidate_review_outcome_id: UUID | None
    reason: str | None
    request_id: str | None
    created_at: datetime

    @classmethod
    def from_record(
        cls,
        record: ReconciliationReviewActionRecord,
    ) -> ReconciliationReviewActionResponse:
        return cls(
            id=record.id,
            reconciliation_review_id=record.reconciliation_review_id,
            bank_transaction_id=record.bank_transaction_id,
            match_run_id=record.match_run_id,
            actor_user_id=record.actor_user_id,
            actor_membership_id=record.actor_membership_id,
            action_type=record.action_type,
            candidate_review_outcome_id=record.candidate_review_outcome_id,
            reason=record.reason,
            request_id=record.request_id,
            created_at=record.created_at,
        )


class ReconciliationOutcomeResponse(BaseModel):
    id: UUID
    reconciliation_review_id: UUID
    bank_transaction_id: UUID
    match_run_id: UUID
    matched_review_outcome_id: UUID | None
    actor_user_id: UUID
    actor_membership_id: UUID
    outcome_type: str
    reason: str | None
    request_id: str | None
    created_at: datetime

    @classmethod
    def from_record(cls, record: ReconciliationOutcomeRecord) -> ReconciliationOutcomeResponse:
        return cls(
            id=record.id,
            reconciliation_review_id=record.reconciliation_review_id,
            bank_transaction_id=record.bank_transaction_id,
            match_run_id=record.match_run_id,
            matched_review_outcome_id=record.matched_review_outcome_id,
            actor_user_id=record.actor_user_id,
            actor_membership_id=record.actor_membership_id,
            outcome_type=record.outcome_type,
            reason=record.reason,
            request_id=record.request_id,
            created_at=record.created_at,
        )


class ReconciliationTerminalDecisionResponse(BaseModel):
    review: ReconciliationReviewResponse
    outcome: ReconciliationOutcomeResponse


class ReconciliationReviewHistoryResponse(BaseModel):
    review: ReconciliationReviewResponse
    actions: list[ReconciliationReviewActionResponse]
    outcome: ReconciliationOutcomeResponse | None
