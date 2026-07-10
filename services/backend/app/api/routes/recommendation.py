from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user_id
from app.domain.models import BasketEnvelope
from app.services.container import recommendation_service

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("/basket", response_model=BasketEnvelope)
def get_basket(
    force_refresh: bool = False,
    user_id: str = Depends(get_current_user_id),
) -> BasketEnvelope:
    _ = force_refresh
    return recommendation_service.build_basket(user_id=user_id, k_limit=3)
