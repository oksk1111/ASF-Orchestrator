"""사용자 인증 API.

Google OAuth 로그인 + JWT 세션 관리.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.cache import store
from app.core.security import require_user
from app.models.schemas import Envelope, GoogleLoginRequest, User
from app.services.auth import AuthError, create_jwt_token, verify_google_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/google")
async def google_login(req: GoogleLoginRequest) -> Envelope:
    """Google ID 토큰으로 로그인/회원가입한다.

    프론트엔드에서 Google Sign-In으로 획득한 id_token을 전송하면:
    1. Google tokeninfo로 검증
    2. 사용자 upsert (신규→생성, 기존→last_login 갱신)
    3. JWT 발급
    """
    try:
        google_info = await verify_google_token(req.id_token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    google_id = google_info["sub"]
    if not google_id:
        raise HTTPException(status_code=401, detail="Google 사용자 ID를 확인할 수 없습니다")

    # 사용자 upsert
    user = store.upsert_user(
        google_id=google_id,
        email=google_info.get("email", ""),
        name=google_info.get("name", ""),
        profile_image=google_info.get("picture", ""),
    )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다")

    # JWT 발급
    token = create_jwt_token(user.id, user.role)

    return Envelope(data={
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 30 * 24 * 3600,  # 30 days in seconds
        "user": user.model_dump(),
    })


@router.get("/me")
def get_current_user(user: User = Depends(require_user)) -> Envelope:
    """현재 인증된 사용자 정보를 반환한다."""
    return Envelope(data=user.model_dump())


@router.post("/refresh")
def refresh_token(user: User = Depends(require_user)) -> Envelope:
    """JWT 토큰을 갱신한다."""
    token = create_jwt_token(user.id, user.role)
    return Envelope(data={
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 30 * 24 * 3600,
    })
