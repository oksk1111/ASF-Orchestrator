"""소비자용 REST 라우트 집계."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.prices import router as prices_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(prices_router)
