"""사용자 활동 로깅 미들웨어.

의미 있는 API 호출만 기록한다 (healthz, static, docs 등 제외).
비동기적으로 기록하여 응답 지연을 방지한다.
"""

from __future__ import annotations

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# 로깅 제외 경로 접두사
_SKIP_PREFIXES = (
    "/healthz",
    "/admin/static",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon",
)

# 의미 있는 액션 분류
_ACTION_MAP = {
    "POST /api/v1/auth": "login",
    "POST /api/v1/alerts": "alert_create",
    "DELETE /api/v1/alerts": "alert_delete",
    "POST /api/v1/devices": "device_register",
    "GET /api/v1/items": "item_view",
    "GET /api/v1/prices": "price_view",
    "GET /api/v1/recommendations": "recommendation_view",
}


def _classify_action(method: str, path: str) -> str:
    """요청을 액션 타입으로 분류한다."""
    key = f"{method} {path}"
    for prefix, action in _ACTION_MAP.items():
        if key.startswith(prefix):
            return action
    if path.startswith("/api/"):
        return "api_call"
    if path.startswith("/admin"):
        return "admin_access"
    return "page_view"


def _should_log(path: str) -> bool:
    """이 경로를 로깅해야 하는지 판단한다."""
    if any(path.startswith(p) for p in _SKIP_PREFIXES):
        return False
    # GET / 루트도 제외
    if path == "/":
        return False
    return True


def _extract_user_id(request: Request) -> str:
    """요청에서 사용자 ID를 추출한다 (JWT 또는 쿼리 파라미터)."""
    # Authorization 헤더에서 JWT sub 추출 시도
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer ") and len(auth_header) > 20:
        try:
            from app.services.auth import decode_jwt_token
            payload = decode_jwt_token(auth_header[7:])
            return payload.get("sub", "")
        except Exception:
            pass
    # 쿼리 파라미터에서 user_id 추출
    return request.query_params.get("user_id", "anonymous")


class ActivityLogMiddleware(BaseHTTPMiddleware):
    """사용자 활동을 기록하는 미들웨어."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 로깅 대상이 아닌 경우 건너뛰기
        if not _should_log(request.url.path):
            return response

        # 성공 응답만 로깅 (4xx/5xx 제외 — 단, POST는 예외)
        if response.status_code >= 400 and request.method == "GET":
            return response

        try:
            from app.cache import store

            user_id = _extract_user_id(request)
            action = _classify_action(request.method, request.url.path)
            detail = f"{request.method} {request.url.path}"
            if request.url.query:
                detail += f"?{request.url.query}"

            ip_address = ""
            if request.client:
                ip_address = request.client.host

            user_agent = request.headers.get("user-agent", "")[:200]

            store.log_activity(
                user_id=user_id,
                action=action,
                detail=detail[:500],
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            # 로깅 실패가 응답에 영향을 주지 않도록 한다
            logger.debug("활동 로그 기록 실패", exc_info=True)

        return response
