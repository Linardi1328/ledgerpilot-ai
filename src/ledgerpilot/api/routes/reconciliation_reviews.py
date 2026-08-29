from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ledgerpilot.api.dependencies import get_session, require_permission
from ledgerpilot.api.errors import get_request_id
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.reconciliation.review_schemas import (
    ReconciliationApprovalRequest,
    ReconciliationCandidateSelectionRequest,
    ReconciliationOutcomeResponse,
    ReconciliationReasonRequest,
    ReconciliationReviewActionResponse,
    ReconciliationReviewCreateRequest,
    ReconciliationReviewHistoryResponse,
    ReconciliationReviewResponse,
    ReconciliationTerminalDecisionResponse,
)
from ledgerpilot.reconciliation.review_service import ReconciliationReviewService

router = APIRouter(prefix="/clients/{client_id}/bank-reconciliation")


@router.post(
    "/transactions/{bank_transaction_id}/reviews",
    response_model=ReconciliationReviewResponse,
    status_code=201,
)
def create_reconciliation_review(
    request: Request,
    client_id: UUID,
    bank_transaction_id: UUID,
    payload: ReconciliationReviewCreateRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.CREATE_RECONCILIATION_REVIEW)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationReviewResponse:
    review = ReconciliationReviewService(session=session).create_review(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        match_run_id=payload.match_run_id,
        request_id=get_request_id(request),
    )
    return ReconciliationReviewResponse.from_record(review)


@router.get(
    "/transactions/{bank_transaction_id}/reviews/{reconciliation_review_id}",
    response_model=ReconciliationReviewResponse,
)
def get_reconciliation_review(
    client_id: UUID,
    bank_transaction_id: UUID,
    reconciliation_review_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_RECONCILIATION_HISTORY)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationReviewResponse:
    review = ReconciliationReviewService(session=session).get_review(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        reconciliation_review_id=reconciliation_review_id,
    )
    return ReconciliationReviewResponse.from_record(review)


@router.post(
    "/transactions/{bank_transaction_id}/reviews/{reconciliation_review_id}/candidate-selection",
    response_model=ReconciliationReviewResponse,
)
def select_reconciliation_candidate(
    request: Request,
    client_id: UUID,
    bank_transaction_id: UUID,
    reconciliation_review_id: UUID,
    payload: ReconciliationCandidateSelectionRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.REVIEW_RECONCILIATION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationReviewResponse:
    review = ReconciliationReviewService(session=session).select_candidate(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        reconciliation_review_id=reconciliation_review_id,
        review_outcome_id=payload.review_outcome_id,
        request_id=get_request_id(request),
    )
    return ReconciliationReviewResponse.from_record(review)


@router.post(
    "/transactions/{bank_transaction_id}/reviews/{reconciliation_review_id}/dispute",
    response_model=ReconciliationReviewResponse,
)
def dispute_reconciliation_review(
    request: Request,
    client_id: UUID,
    bank_transaction_id: UUID,
    reconciliation_review_id: UUID,
    payload: ReconciliationReasonRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.REVIEW_RECONCILIATION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationReviewResponse:
    review = ReconciliationReviewService(session=session).dispute(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        reconciliation_review_id=reconciliation_review_id,
        reason=payload.reason,
        request_id=get_request_id(request),
    )
    return ReconciliationReviewResponse.from_record(review)


@router.post(
    "/transactions/{bank_transaction_id}/reviews/{reconciliation_review_id}/reopen",
    response_model=ReconciliationReviewResponse,
)
def reopen_reconciliation_review(
    request: Request,
    client_id: UUID,
    bank_transaction_id: UUID,
    reconciliation_review_id: UUID,
    payload: ReconciliationReasonRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.REVIEW_RECONCILIATION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationReviewResponse:
    review = ReconciliationReviewService(session=session).reopen(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        reconciliation_review_id=reconciliation_review_id,
        reason=payload.reason,
        request_id=get_request_id(request),
    )
    return ReconciliationReviewResponse.from_record(review)


@router.post(
    "/transactions/{bank_transaction_id}/reviews/{reconciliation_review_id}/approve",
    response_model=ReconciliationTerminalDecisionResponse,
)
def approve_reconciliation_match(
    request: Request,
    client_id: UUID,
    bank_transaction_id: UUID,
    reconciliation_review_id: UUID,
    payload: ReconciliationApprovalRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.APPROVE_RECONCILIATION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationTerminalDecisionResponse:
    review, outcome = ReconciliationReviewService(session=session).approve_match(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        reconciliation_review_id=reconciliation_review_id,
        note=payload.note,
        request_id=get_request_id(request),
    )
    return ReconciliationTerminalDecisionResponse(
        review=ReconciliationReviewResponse.from_record(review),
        outcome=ReconciliationOutcomeResponse.from_record(outcome),
    )


@router.post(
    "/transactions/{bank_transaction_id}/reviews/{reconciliation_review_id}/mark-unmatched",
    response_model=ReconciliationTerminalDecisionResponse,
)
def mark_reconciliation_unmatched(
    request: Request,
    client_id: UUID,
    bank_transaction_id: UUID,
    reconciliation_review_id: UUID,
    payload: ReconciliationReasonRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.APPROVE_RECONCILIATION)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationTerminalDecisionResponse:
    review, outcome = ReconciliationReviewService(session=session).mark_unmatched(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        reconciliation_review_id=reconciliation_review_id,
        reason=payload.reason,
        request_id=get_request_id(request),
    )
    return ReconciliationTerminalDecisionResponse(
        review=ReconciliationReviewResponse.from_record(review),
        outcome=ReconciliationOutcomeResponse.from_record(outcome),
    )


@router.get(
    "/transactions/{bank_transaction_id}/reviews/{reconciliation_review_id}/history",
    response_model=ReconciliationReviewHistoryResponse,
)
def get_reconciliation_review_history(
    client_id: UUID,
    bank_transaction_id: UUID,
    reconciliation_review_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_RECONCILIATION_HISTORY)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationReviewHistoryResponse:
    history = ReconciliationReviewService(session=session).history(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        reconciliation_review_id=reconciliation_review_id,
    )
    return ReconciliationReviewHistoryResponse(
        review=ReconciliationReviewResponse.from_record(history.review),
        actions=[
            ReconciliationReviewActionResponse.from_record(action)
            for action in history.actions
        ],
        outcome=(
            ReconciliationOutcomeResponse.from_record(history.outcome)
            if history.outcome is not None
            else None
        ),
    )
