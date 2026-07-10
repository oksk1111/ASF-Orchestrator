from __future__ import annotations

from fastapi import APIRouter

from app.domain.models import ForecastEnvelope
from app.services.container import forecasting_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/pricing", response_model=ForecastEnvelope)
def get_forecasts(refresh: bool = False) -> ForecastEnvelope:
    if refresh:
        return forecasting_service.refresh_forecasts()
    return forecasting_service.list_forecasts()
