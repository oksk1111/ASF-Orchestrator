"""Google OAuth 토큰 검증 + JWT 세션 관리."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class AuthError(Exception):
    """인증 관련 오류."""
    pass


async def verify_google_token(id_token: str) -> dict[str, Any]:
    """Google ID 토큰을 검증하고 사용자 정보를 반환한다.

    Returns:
        {"sub": google_id, "email": str, "name": str, "picture": str}

    Raises:
        AuthError: 토큰 검증 실패.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(GOOGLE_TOKEN_INFO_URL, params={"id_token": id_token})
        except httpx.HTTPError as exc:
            raise AuthError(f"Google 토큰 검증 네트워크 오류: {exc}") from exc

    if resp.status_code != 200:
        raise AuthError(f"Google 토큰 검증 실패 (HTTP {resp.status_code})")

    data = resp.json()

    # audience(aud) 검증 — google_client_id가 설정된 경우만
    if settings.google_client_id:
        if data.get("aud") != settings.google_client_id:
            raise AuthError("토큰 audience가 일치하지 않습니다")

    # 만료 검증
    exp = data.get("exp")
    if exp:
        try:
            if int(exp) < int(datetime.now(timezone.utc).timestamp()):
                raise AuthError("토큰이 만료되었습니다")
        except (ValueError, TypeError):
            pass

    return {
        "sub": data.get("sub", ""),
        "email": data.get("email", ""),
        "name": data.get("name", ""),
        "picture": data.get("picture", ""),
    }


def create_jwt_token(user_id: int, role: str = "user") -> str:
    """JWT 토큰을 생성한다.

    Args:
        user_id: DB 유저 ID.
        role: 유저 역할 ("user" | "admin").

    Returns:
        인코딩된 JWT 문자열.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> dict[str, Any]:
    """JWT 토큰을 디코딩한다.

    Returns:
        {"sub": str(user_id), "role": str, "iat": int, "exp": int}

    Raises:
        AuthError: 토큰 디코딩/검증 실패.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("토큰이 만료되었습니다")
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"유효하지 않은 토큰: {exc}")
