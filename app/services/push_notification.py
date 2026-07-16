"""Firebase Cloud Messaging (FCM) Push 알림 발송 서비스.

FCM HTTP v1 API를 사용하여 가격 알림을 발송한다.
서비스 계정 인증으로 access token을 획득하여 사용.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SCOPES = "https://www.googleapis.com/auth/firebase.messaging"

# 캐시된 access token
_cached_token: str = ""
_token_expires_at: datetime = datetime.min.replace(tzinfo=timezone.utc)


class FCMError(Exception):
    """FCM 관련 오류."""
    pass


async def _get_access_token() -> str:
    """서비스 계정을 사용하여 OAuth2 access token을 획득한다."""
    global _cached_token, _token_expires_at

    now = datetime.now(timezone.utc)
    if _cached_token and _token_expires_at > now + timedelta(minutes=5):
        return _cached_token

    sa_path = settings.firebase_service_account_json
    if not sa_path:
        raise FCMError("FIREBASE_SERVICE_ACCOUNT_JSON이 설정되지 않았습니다")

    sa_file = Path(sa_path)
    if not sa_file.exists():
        raise FCMError(f"서비스 계정 파일을 찾을 수 없습니다: {sa_path}")

    try:
        sa_data = json.loads(sa_file.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise FCMError(f"서비스 계정 파일 읽기 실패: {exc}") from exc

    # JWT assertion 생성 (서비스 계정 인증)
    import jwt as pyjwt

    now_ts = int(now.timestamp())
    assertion_payload = {
        "iss": sa_data["client_email"],
        "sub": sa_data["client_email"],
        "aud": _GOOGLE_TOKEN_URL,
        "iat": now_ts,
        "exp": now_ts + 3600,
        "scope": _SCOPES,
    }
    assertion = pyjwt.encode(
        assertion_payload,
        sa_data["private_key"],
        algorithm="RS256",
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )

    if resp.status_code != 200:
        raise FCMError(f"Google OAuth2 토큰 획득 실패: {resp.text[:200]}")

    token_data = resp.json()
    _cached_token = token_data["access_token"]
    _token_expires_at = now + timedelta(seconds=token_data.get("expires_in", 3600))
    return _cached_token


async def send_push_notification(
    device_tokens: list[str],
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """FCM으로 push 알림을 발송한다.

    Args:
        device_tokens: FCM 디바이스 토큰 목록.
        title: 알림 제목.
        body: 알림 본문.
        data: 추가 데이터 페이로드.

    Returns:
        성공적으로 발송된 건수.
    """
    if not settings.firebase_project_id:
        logger.warning("FIREBASE_PROJECT_ID가 설정되지 않아 push 발송을 건너뜁니다")
        return 0

    if not device_tokens:
        return 0

    try:
        access_token = await _get_access_token()
    except FCMError as exc:
        logger.error("FCM access token 획득 실패: %s", exc)
        return 0

    url = _FCM_SEND_URL.format(project_id=settings.firebase_project_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    success_count = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for token in device_tokens:
            message: dict[str, Any] = {
                "message": {
                    "token": token,
                    "notification": {
                        "title": title,
                        "body": body,
                    },
                }
            }
            if data:
                message["message"]["data"] = data

            try:
                resp = await client.post(url, headers=headers, json=message)
                if resp.status_code == 200:
                    success_count += 1
                else:
                    logger.warning(
                        "FCM 발송 실패 (token=%s...): HTTP %d %s",
                        token[:20], resp.status_code, resp.text[:100],
                    )
            except httpx.HTTPError as exc:
                logger.warning("FCM 발송 네트워크 오류: %s", exc)

    logger.info("FCM push 발송 완료: %d/%d 성공", success_count, len(device_tokens))
    return success_count


async def send_price_alert_push(
    device_tokens: list[str],
    item_name: str,
    target_price: int,
    actual_price: int,
    direction: str,
) -> int:
    """가격 알림 전용 push를 발송한다."""
    if direction == "above":
        title = f"🔺 {item_name} 가격 상승 알림"
        body = f"현재가 {actual_price:,}원이 목표가 {target_price:,}원을 넘었습니다"
    else:
        title = f"🔻 {item_name} 가격 하락 알림"
        body = f"현재가 {actual_price:,}원이 목표가 {target_price:,}원 이하입니다"

    data = {
        "type": "price_alert",
        "item_name": item_name,
        "target_price": str(target_price),
        "actual_price": str(actual_price),
        "direction": direction,
    }

    return await send_push_notification(device_tokens, title, body, data)
