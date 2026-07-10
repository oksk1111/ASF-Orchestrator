from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user_id
from app.domain.models import CheckoutEnvelope, CheckoutRequest
from app.services.container import checkout_service

router = APIRouter(tags=["checkout"])


@router.post("/checkout", response_model=CheckoutEnvelope)
def checkout(
    request: CheckoutRequest,
    token_user_id: str = Depends(get_current_user_id),
) -> CheckoutEnvelope:
    if request.user_id != token_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user mismatch",
        )
    return checkout_service.process_checkout(request)
