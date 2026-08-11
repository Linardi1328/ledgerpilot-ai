from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ledgerpilot.api.dependencies import get_session
from ledgerpilot.api.errors import get_request_id

router = APIRouter(prefix="/health")


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
def ready(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any] | JSONResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        content: dict[str, Any] = {
            "status": "error",
            "checks": {"database": "unavailable"},
            "request_id": get_request_id(request),
        }
        return JSONResponse(status_code=503, content=content)
    return {"status": "ok", "checks": {"database": "ok"}}
