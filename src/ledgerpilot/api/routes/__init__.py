from __future__ import annotations

from fastapi import APIRouter

from ledgerpilot.api.routes import accounting, context, documents, extractions, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(context.router, tags=["context"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(extractions.router, tags=["extractions"])
api_router.include_router(accounting.router, tags=["accounting"])
