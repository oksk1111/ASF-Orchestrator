from fastapi import APIRouter

from app.domain.models import CalculateRouteRequest, RouteEnvelope
from app.services.container import logistics_service

router = APIRouter(prefix="/logistics", tags=["logistics"])


@router.post("/route", response_model=RouteEnvelope)
def calculate_route(request: CalculateRouteRequest) -> RouteEnvelope:
    return logistics_service.calculate_route(request)
