from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ledgerpilot.accounting.rules import AccountingDecisionPolicy
from ledgerpilot.accounting.schemas import (
    AccountingDecisionRunResponse,
    AccountingDecisionRunSummaryResponse,
)
from ledgerpilot.accounting.service import AccountingDecisionService
from ledgerpilot.api.dependencies import (
    get_accounting_decision_policy,
    get_session,
    require_permission,
)
from ledgerpilot.api.errors import get_request_id
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal

router = APIRouter(
    prefix="/clients/{client_id}/documents/{document_id}/extractions/{extraction_run_id}"
    "/accounting-decisions"
)


@router.post(
    "",
    response_model=AccountingDecisionRunResponse,
    status_code=201,
)
def start_accounting_decision(
    request: Request,
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.RUN_ACCOUNTING_DECISION)),
    ],
    session: Annotated[Session, Depends(get_session)],
    policy: Annotated[AccountingDecisionPolicy, Depends(get_accounting_decision_policy)],
) -> AccountingDecisionRunResponse:
    bundle = AccountingDecisionService(session=session, policy=policy).start_decision_run(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        request_id=get_request_id(request),
    )
    return AccountingDecisionRunResponse.from_bundle(bundle)


@router.get(
    "",
    response_model=list[AccountingDecisionRunSummaryResponse],
)
def list_accounting_decisions(
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.REVIEW_RECOMMENDATIONS)),
    ],
    session: Annotated[Session, Depends(get_session)],
    policy: Annotated[AccountingDecisionPolicy, Depends(get_accounting_decision_policy)],
) -> list[AccountingDecisionRunSummaryResponse]:
    runs = AccountingDecisionService(session=session, policy=policy).list_decision_runs(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
    )
    return [AccountingDecisionRunSummaryResponse.from_run(run) for run in runs]


@router.get(
    "/{decision_run_id}",
    response_model=AccountingDecisionRunResponse,
)
def get_accounting_decision(
    client_id: UUID,
    document_id: UUID,
    extraction_run_id: UUID,
    decision_run_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.REVIEW_RECOMMENDATIONS)),
    ],
    session: Annotated[Session, Depends(get_session)],
    policy: Annotated[AccountingDecisionPolicy, Depends(get_accounting_decision_policy)],
) -> AccountingDecisionRunResponse:
    bundle = AccountingDecisionService(session=session, policy=policy).get_decision_run(
        principal=principal,
        client_id=client_id,
        document_id=document_id,
        extraction_run_id=extraction_run_id,
        decision_run_id=decision_run_id,
    )
    return AccountingDecisionRunResponse.from_bundle(bundle)
