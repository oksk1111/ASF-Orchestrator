"""API 라우트 총괄."""

from fastapi import APIRouter

from app.api.routes.alerts import router as alerts_router
from app.api.routes.auth import router as auth_router
from app.api.routes.fresh_alert import router as fresh_alert_router
from app.api.routes.health import router as health_router
from app.api.routes.prices import router as prices_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(prices_router)
api_router.include_router(alerts_router)
api_router.include_router(fresh_alert_router)
api_router.include_router(auth_router)
