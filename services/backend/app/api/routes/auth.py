from fastapi import APIRouter

from app.core.security import create_access_token
from app.domain.models import TokenRequest, TokenResponse
from app.repositories.in_memory import repo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def issue_token(request: TokenRequest) -> TokenResponse:
    target_user_id = request.user_id or repo.get_default_user_id()
    user = repo.get_user(target_user_id)
    if user is None:
        target_user_id = repo.get_default_user_id()

    access_token = create_access_token(target_user_id)
    return TokenResponse(access_token=access_token, user_id=target_user_id)
