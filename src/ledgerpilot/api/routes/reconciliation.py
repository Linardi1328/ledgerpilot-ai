from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ledgerpilot.api.dependencies import get_session, get_settings, require_permission
from ledgerpilot.api.errors import ApiError, get_request_id
from ledgerpilot.core.config import Environment, Settings
from ledgerpilot.identity.permissions import Permission
from ledgerpilot.identity.principal import Principal
from ledgerpilot.reconciliation.api_service import (
    SYNTHETIC_API_PROVIDER_NAME,
    SYNTHETIC_API_PROVIDER_VERSION,
    ReconciliationApiService,
)
from ledgerpilot.reconciliation.schemas import (
    BankImportBatchResponse,
    BankImportResponse,
    BankTransactionResponse,
    ReconciliationCandidateResponse,
    ReconciliationMatchResponse,
    ReconciliationMatchRunResponse,
    SyntheticBankImportCreateRequest,
)

router = APIRouter(prefix="/clients/{client_id}/bank-reconciliation")


@router.post(
    "/imports/synthetic",
    response_model=BankImportResponse,
    status_code=201,
)
def create_synthetic_bank_import(
    request: Request,
    response: Response,
    client_id: UUID,
    payload: SyntheticBankImportCreateRequest,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.IMPORT_BANK_TRANSACTIONS)),
    ],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BankImportResponse:
    if settings.env == Environment.PRODUCTION:
        raise ApiError(
            status_code=403,
            code="synthetic_bank_import_disabled",
            message="Synthetic bank imports are disabled in production.",
        )
    batch = payload.to_batch(
        firm_id=principal.firm_id,
        client_id=client_id,
        provider_name=SYNTHETIC_API_PROVIDER_NAME,
        provider_version=SYNTHETIC_API_PROVIDER_VERSION,
    )
    result = ReconciliationApiService(session=session).persist_import_batch(
        principal=principal,
        batch=batch,
        request_id=get_request_id(request),
    )
    if not result.created:
        response.status_code = 200
    return BankImportResponse(
        created=result.created,
        batch=BankImportBatchResponse.from_record(result.batch),
        transactions=[
            BankTransactionResponse.from_record(transaction) for transaction in result.transactions
        ],
    )


@router.get(
    "/imports",
    response_model=list[BankImportBatchResponse],
)
def list_bank_imports(
    client_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_BANK_TRANSACTIONS)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> list[BankImportBatchResponse]:
    batches = ReconciliationApiService(session=session).list_import_batches(
        principal=principal,
        client_id=client_id,
    )
    return [BankImportBatchResponse.from_record(batch) for batch in batches]


@router.get(
    "/imports/{import_batch_id}",
    response_model=BankImportBatchResponse,
)
def get_bank_import(
    client_id: UUID,
    import_batch_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_BANK_TRANSACTIONS)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> BankImportBatchResponse:
    batch = ReconciliationApiService(session=session).get_import_batch(
        principal=principal,
        client_id=client_id,
        import_batch_id=import_batch_id,
    )
    return BankImportBatchResponse.from_record(batch)


@router.get(
    "/imports/{import_batch_id}/transactions",
    response_model=list[BankTransactionResponse],
)
def list_bank_transactions_for_import(
    client_id: UUID,
    import_batch_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_BANK_TRANSACTIONS)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> list[BankTransactionResponse]:
    transactions = ReconciliationApiService(session=session).list_transactions_for_batch(
        principal=principal,
        client_id=client_id,
        import_batch_id=import_batch_id,
    )
    return [BankTransactionResponse.from_record(transaction) for transaction in transactions]


@router.get(
    "/transactions/{bank_transaction_id}",
    response_model=BankTransactionResponse,
)
def get_bank_transaction(
    client_id: UUID,
    bank_transaction_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_BANK_TRANSACTIONS)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> BankTransactionResponse:
    transaction = ReconciliationApiService(session=session).get_transaction(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
    )
    return BankTransactionResponse.from_record(transaction)


@router.post(
    "/transactions/{bank_transaction_id}/match-runs",
    response_model=ReconciliationMatchResponse,
    status_code=201,
)
def generate_reconciliation_match_run(
    request: Request,
    client_id: UUID,
    bank_transaction_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.RUN_RECONCILIATION_MATCHING)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> ReconciliationMatchResponse:
    bundle = ReconciliationApiService(session=session).generate_match_run(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        request_id=get_request_id(request),
    )
    return ReconciliationMatchResponse(
        run=ReconciliationMatchRunResponse.from_record(bundle.run),
        candidates=[
            ReconciliationCandidateResponse.from_record(candidate)
            for candidate in bundle.candidates
        ],
    )


@router.get(
    "/transactions/{bank_transaction_id}/match-runs",
    response_model=list[ReconciliationMatchRunResponse],
)
def list_reconciliation_match_runs(
    client_id: UUID,
    bank_transaction_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_RECONCILIATION_MATCHES)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> list[ReconciliationMatchRunResponse]:
    runs = ReconciliationApiService(session=session).list_match_runs(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
    )
    return [ReconciliationMatchRunResponse.from_record(run) for run in runs]


@router.get(
    "/transactions/{bank_transaction_id}/match-runs/{match_run_id}/candidates",
    response_model=list[ReconciliationCandidateResponse],
)
def list_reconciliation_candidates(
    client_id: UUID,
    bank_transaction_id: UUID,
    match_run_id: UUID,
    principal: Annotated[
        Principal,
        Depends(require_permission(Permission.VIEW_RECONCILIATION_MATCHES)),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> list[ReconciliationCandidateResponse]:
    candidates = ReconciliationApiService(session=session).list_candidates(
        principal=principal,
        client_id=client_id,
        bank_transaction_id=bank_transaction_id,
        match_run_id=match_run_id,
    )
    return [ReconciliationCandidateResponse.from_record(candidate) for candidate in candidates]
