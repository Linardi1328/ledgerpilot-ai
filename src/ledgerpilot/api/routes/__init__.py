from __future__ import annotations

from fastapi import APIRouter

from ledgerpilot.api.routes import context, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(context.router, tags=["context"])
