from fastapi import APIRouter

from app.api.routes import auth, checkout, forecast, fresh_alert, health, ingestion, logistics, recommendation

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(recommendation.router)
api_router.include_router(forecast.router)
api_router.include_router(ingestion.router)
api_router.include_router(logistics.router)
api_router.include_router(checkout.router)
api_router.include_router(fresh_alert.router)
