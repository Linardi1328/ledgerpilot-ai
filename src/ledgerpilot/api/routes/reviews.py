from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ledgerpilot.api.dependencies import get_session, require_permission
from ledgerpilot.api.errors import get_request_id
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.review.history import ReviewHistoryService
from ledgerpilot.review.interactions import ReviewInteractionService
from ledgerpilot.review.outcomes import ReviewOutcomeService
from ledgerpilot.review.schemas import (
    ReviewApprovalRequest,
    ReviewAuditEventResponse,
    ReviewCommentCreateRequest,
    ReviewCommentResponse,
    ReviewEscalationRequest,
    ReviewHistoryResponse,
    ReviewInformationRequestCreateRequest,
    ReviewInformationResponseCreateRequest,
    ReviewInteractionResponse,
    ReviewOutcomeResponse,
    ReviewRejectionRequest,
    ReviewResolutionResponse,
    ReviewTaskCreateRequest,
    ReviewTaskResponse,
)
from ledgerpilot.review.service import ReviewTaskService

router = APIRouter(
    prefix="/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}"
    "/accounting-decisions/{decision_run_id}/review-tasks"
)


@router.post("", response_model=ReviewTaskResponse, status_code=201)
def create_review_task(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    payload: ReviewTaskCreateRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.CREATE_REVIEW_TASK)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewTaskResponse:
    task = ReviewTaskService(session=session).create_task(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        owner_membership_id=payload.owner_membership_id,
        request_id=get_request_id(request),
    )
    return ReviewTaskResponse.from_task(task)


@router.get("", response_model=list[ReviewTaskResponse])
def list_review_tasks(
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_REVIEW_TASK)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> list[ReviewTaskResponse]:
    tasks = ReviewTaskService(session=session).list_tasks(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
    )
    return [ReviewTaskResponse.from_task(task) for task in tasks]


@router.get("/{review_task_id}", response_model=ReviewTaskResponse)
def get_review_task(
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_REVIEW_TASK)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewTaskResponse:
    task = ReviewTaskService(session=session).get_task(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
    )
    return ReviewTaskResponse.from_task(task)


@router.post("/{review_task_id}/escalations", response_model=ReviewTaskResponse)
def escalate_review_task(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    payload: ReviewEscalationRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.ESCALATE_TRANSACTION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewTaskResponse:
    task = ReviewTaskService(session=session).escalate_to_senior(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
        senior_membership_id=payload.senior_membership_id,
        reason=payload.reason,
        request_id=get_request_id(request),
    )
    return ReviewTaskResponse.from_task(task)


@router.post("/{review_task_id}/comments", response_model=ReviewCommentResponse, status_code=201)
def add_review_comment(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    payload: ReviewCommentCreateRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.ADD_REVIEW_COMMENT)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewCommentResponse:
    comment = ReviewInteractionService(session=session).add_comment(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
        body=payload.body,
        request_id=get_request_id(request),
    )
    return ReviewCommentResponse.from_comment(comment)


@router.post(
    "/{review_task_id}/information-requests",
    response_model=ReviewInteractionResponse,
    status_code=201,
)
def request_review_information(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    payload: ReviewInformationRequestCreateRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.REQUEST_INFORMATION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewInteractionResponse:
    task, comment = ReviewInteractionService(session=session).request_information(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
        body=payload.body,
        request_id=get_request_id(request),
    )
    return ReviewInteractionResponse(
        task=ReviewTaskResponse.from_task(task),
        comment=ReviewCommentResponse.from_comment(comment),
    )


@router.get("/{review_task_id}/information-request", response_model=ReviewCommentResponse)
def get_outstanding_information_request(
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_INFORMATION_REQUEST)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewCommentResponse:
    comment = ReviewInteractionService(session=session).get_information_request(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
    )
    return ReviewCommentResponse.from_comment(comment)


@router.post(
    "/{review_task_id}/information-responses",
    response_model=ReviewInteractionResponse,
    status_code=201,
)
def respond_to_review_information(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    payload: ReviewInformationResponseCreateRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.RESPOND_TO_INFORMATION_REQUEST)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewInteractionResponse:
    task, comment = ReviewInteractionService(session=session).respond_to_information_request(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
        body=payload.body,
        request_id=get_request_id(request),
    )
    return ReviewInteractionResponse(
        task=ReviewTaskResponse.from_task(task),
        comment=ReviewCommentResponse.from_comment(comment),
    )


@router.post("/{review_task_id}/approve", response_model=ReviewResolutionResponse)
def approve_review_task(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    payload: ReviewApprovalRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.APPROVE_ORDINARY_TRANSACTION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewResolutionResponse:
    task, outcome = ReviewOutcomeService(session=session).approve(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
        note=payload.note,
        request_id=get_request_id(request),
    )
    return ReviewResolutionResponse(
        task=ReviewTaskResponse.from_task(task),
        outcome=ReviewOutcomeResponse.from_outcome(outcome),
    )


@router.post("/{review_task_id}/reject", response_model=ReviewResolutionResponse)
def reject_review_task(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    payload: ReviewRejectionRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.REJECT_TRANSACTION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewResolutionResponse:
    task, outcome = ReviewOutcomeService(session=session).reject(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
        reason=payload.reason,
        request_id=get_request_id(request),
    )
    return ReviewResolutionResponse(
        task=ReviewTaskResponse.from_task(task),
        outcome=ReviewOutcomeResponse.from_outcome(outcome),
    )


@router.get("/{review_task_id}/history", response_model=ReviewHistoryResponse)
def get_review_history(
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    review_task_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_REVIEW_HISTORY)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReviewHistoryResponse:
    task, comments, outcome, audit_events = ReviewHistoryService(session=session).get_history(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
        review_task_id=review_task_id,
    )
    return ReviewHistoryResponse(
        task=ReviewTaskResponse.from_task(task),
        comments=[ReviewCommentResponse.from_comment(comment) for comment in comments],
        outcome=ReviewOutcomeResponse.from_outcome(outcome) if outcome is not None else None,
        audit_events=[ReviewAuditEventResponse.from_event(event) for event in audit_events],
    )
