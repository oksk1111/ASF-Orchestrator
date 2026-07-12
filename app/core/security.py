"""인증/보안 유틸.

- 관리자 웹: HTTP Basic (secrets.compare_digest로 타이밍 공격 방지)
- 소비자 API: 선택적 Bearer 토큰
"""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

_basic = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_basic)) -> str:
    """관리자 HTTP Basic 인증을 강제한다.

    Returns:
        인증된 사용자명.

    Raises:
        HTTPException: 자격 증명이 일치하지 않을 때 401.
    """
    user_ok = secrets.compare_digest(credentials.username, settings.admin_username)
    pass_ok = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="관리자 인증 실패",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


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
