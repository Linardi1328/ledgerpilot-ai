from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ledgerpilot.api.dependencies import get_session, require_permission
from ledgerpilot.api.errors import get_request_id
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.review.schemas import ReviewTaskCreateRequest, ReviewTaskResponse
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
