from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def get_request_id(request: Request) -> str | None:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str):
        return request_id
    return None


def error_payload(code: str, message: str, request_id: str | None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ApiError):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, get_request_id(request)),
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    code = "not_found" if exc.status_code == 404 else "http_error"
    message = "Not found." if exc.status_code == 404 else "Request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(code, message, get_request_id(request)),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    logger.info("Request validation failed", extra={"request_id": get_request_id(request)})
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "invalid_request",
            "Request validation failed.",
            get_request_id(request),
        ),
    )


async def sqlalchemy_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, SQLAlchemyError):
        raise exc
    logger.error(
        "Database error",
        extra={
            "request_id": get_request_id(request),
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content=error_payload("server_error", "Internal server error.", get_request_id(request)),
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error", extra={"request_id": get_request_id(request)})
    return JSONResponse(
        status_code=500,
        content=error_payload("server_error", "Internal server error.", get_request_id(request)),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
