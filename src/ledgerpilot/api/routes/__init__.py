from __future__ import annotations

from fastapi import APIRouter

from ledgerpilot.api.routes import context, documents, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(context.router, tags=["context"])
api_router.include_router(documents.router, tags=["documents"])
