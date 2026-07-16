"""인증 & 인가 유틸리티.

- 관리자 웹: HTTP Basic 인증 (기존 유지)
- 소비자 API: 선택적 Bearer 토큰 (빈 설정이면 공개)
- 사용자 인증: JWT 기반 (Google OAuth 로그인 후 발급)
"""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer

from app.core.config import settings
from app.models.schemas import User

_basic = HTTPBasic(auto_error=False)
_bearer = HTTPBearer(auto_error=False)


# ─── 관리자 웹 인증 (HTTP Basic) ──────────────────────────────────────────────


def require_admin(credentials: HTTPBasicCredentials | None = Depends(_basic)) -> str:
    """HTTP Basic 인증. 실패 시 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Basic"},
        )
    correct_user = secrets.compare_digest(credentials.username, settings.admin_username)
    correct_pass = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 관리자 계정",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ─── 소비자 API 인증 (선택적 Bearer) ─────────────────────────────────────────


def require_consumer(authorization: str | None = Header(default=None)) -> None:
    """소비자 API 토큰을 검증한다.

    CONSUMER_API_TOKEN이 비어 있으면 인증 없이 통과(공개).
    설정된 경우 `Authorization: Bearer <token>` 헤더를 요구한다.
    """
    token = settings.consumer_api_token
    if not token:
        return
    expected = f"Bearer {token}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="소비자 API 토큰이 유효하지 않습니다",
        )


# ─── JWT 사용자 인증 ──────────────────────────────────────────────────────────


def require_user(credentials=Depends(_bearer)) -> User:
    """JWT 인증. 유효한 사용자 User 객체를 반환한다.

    Raises:
        HTTPException(401): 토큰 없음/만료/유효하지 않음.
        HTTPException(403): 비활성화된 계정.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
        )

    from app.services.auth import AuthError, decode_jwt_token

    try:
        payload = decode_jwt_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰 (사용자 ID 없음)",
        )

    from app.cache import store

    user = store.get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다",
        )

    return user


def require_admin_user(user: User = Depends(require_user)) -> User:
    """관리자 역할을 요구한다.

    Raises:
        HTTPException(403): admin 역할이 아님.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )
    return user
