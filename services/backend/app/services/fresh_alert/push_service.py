"""FreshAlert FCM 푸시 알림 서비스.

Firebase Cloud Messaging을 통한 푸시 알림 발송을 담당하는 모듈.
Firebase가 초기화되지 않은 개발 환경에서는 로그 출력으로 대체한다.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOPIC_DAILY_RECOMMEND = "daily_recommendations"
TOPIC_PRICE_ALERT = "price_alerts"

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_firebase_initialized: bool = False


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init_firebase(credentials_path: str | None = None) -> None:
    """Firebase Admin SDK를 초기화한다.

    이미 초기화된 경우 중복 초기화를 방지한다.
    credentials_path가 None이면 GOOGLE_APPLICATION_CREDENTIALS 환경변수를 사용한다.
    어떤 인증 정보도 없으면 개발 모드로 동작하며 경고 로그를 남긴다.

    Args:
        credentials_path: Firebase 서비스 계정 JSON 키 파일 경로.
            None이면 환경변수에서 자동 탐색.
    """
    global _firebase_initialized

    if _firebase_initialized:
        logger.debug("Firebase already initialized, skipping")
        return

    # 이미 다른 곳에서 firebase_admin이 초기화된 경우
    if firebase_admin._apps:
        _firebase_initialized = True
        logger.debug("Firebase app already exists, marking as initialized")
        return

    resolved_path = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not resolved_path:
        logger.warning(
            "Firebase credentials not configured. "
            "Push notifications will be logged only (dev mode). "
            "Set GOOGLE_APPLICATION_CREDENTIALS or pass credentials_path to enable."
        )
        return

    try:
        cred = credentials.Certificate(resolved_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized successfully")
    except Exception as exc:
        logger.error("Failed to initialize Firebase Admin SDK: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Push sending functions
# ---------------------------------------------------------------------------


async def send_push(
    token: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> bool:
    """단일 디바이스에 푸시 알림을 발송한다.

    Args:
        token: FCM 디바이스 토큰
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 페이로드 (딥링크 등)

    Returns:
        발송 성공 여부. 실패 시에도 예외를 발생시키지 않고 False를 반환한다.
    """
    if not _firebase_initialized:
        _log_dev_push(token=token, title=title, body=body, data=data)
        return True

    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=token,
        )
        response = messaging.send(message)
        logger.info("Push sent successfully: message_id=%s", response)
        return True
    except messaging.UnregisteredError:
        logger.warning("Token unregistered, should be removed: token=%s...", token[:20])
        return False
    except Exception as exc:
        logger.error("Failed to send push notification: %s", exc)
        return False


async def send_push_batch(
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> dict[str, int]:
    """여러 디바이스에 푸시 알림을 일괄 발송한다 (multicast).

    Args:
        tokens: FCM 디바이스 토큰 리스트
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 페이로드

    Returns:
        {"success": 성공 건수, "failure": 실패 건수}
    """
    if not tokens:
        return {"success": 0, "failure": 0}

    if not _firebase_initialized:
        for token in tokens:
            _log_dev_push(token=token, title=title, body=body, data=data)
        return {"success": len(tokens), "failure": 0}

    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=tokens,
        )
        response = messaging.send_each_for_multicast(message)
        logger.info(
            "Batch push sent: success=%d, failure=%d",
            response.success_count,
            response.failure_count,
        )
        return {
            "success": response.success_count,
            "failure": response.failure_count,
        }
    except Exception as exc:
        logger.error("Failed to send batch push: %s", exc)
        return {"success": 0, "failure": len(tokens)}


async def send_topic_push(
    topic: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> bool:
    """토픽에 푸시 알림을 발송한다.

    구독 중인 모든 디바이스에 알림을 전달한다.

    Args:
        topic: FCM 토픽 이름 (예: "daily_recommendations")
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 페이로드

    Returns:
        발송 성공 여부
    """
    if not _firebase_initialized:
        _log_dev_push(topic=topic, title=title, body=body, data=data)
        return True

    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            topic=topic,
        )
        response = messaging.send(message)
        logger.info("Topic push sent: topic=%s, message_id=%s", topic, response)
        return True
    except Exception as exc:
        logger.error("Failed to send topic push: topic=%s, error=%s", topic, exc)
        return False


# ---------------------------------------------------------------------------
# Notification payload builders
# ---------------------------------------------------------------------------


def build_recommend_payload(items: list[dict]) -> dict[str, str]:
    """추천 알림용 FCM data 페이로드를 생성한다.

    딥링크를 통해 앱에서 추천 목록 화면으로 이동할 수 있도록
    item_ids, names, scores를 포함한다.

    Args:
        items: 추천 품목 리스트.
            각 dict는 item_id, item_name, recommend_score 키를 포함해야 한다.

    Returns:
        FCM data 페이로드 (모든 값은 문자열)
    """
    item_ids = [item["item_id"] for item in items]
    names = [item["item_name"] for item in items]
    scores = [str(item.get("recommend_score", 0)) for item in items]

    return {
        "type": "recommend",
        "item_ids": json.dumps(item_ids, ensure_ascii=False),
        "item_names": json.dumps(names, ensure_ascii=False),
        "scores": json.dumps(scores, ensure_ascii=False),
        "count": str(len(items)),
        "action": "open_recommend_list",
    }


def build_keyword_payload(
    item_id: str,
    item_name: str,
    price: int,
    drop_rate: float,
) -> dict[str, str]:
    """키워드 알림용 FCM data 페이로드를 생성한다.

    Args:
        item_id: 품목 ID
        item_name: 품목명
        price: 현재 가격
        drop_rate: 하락률 (예: -12.5)

    Returns:
        FCM data 페이로드 (모든 값은 문자열)
    """
    return {
        "type": "keyword",
        "item_id": item_id,
        "item_name": item_name,
        "price": str(price),
        "drop_rate": f"{drop_rate:.1f}",
        "action": "open_item_detail",
    }


def build_category_payload(
    category_name: str,
    top_items: list[dict],
) -> dict[str, str]:
    """카테고리 알림용 FCM data 페이로드를 생성한다.

    Args:
        category_name: 카테고리명 (예: "과일류")
        top_items: 해당 카테고리 추천 품목 리스트.
            각 dict는 item_id, item_name 키를 포함해야 한다.

    Returns:
        FCM data 페이로드 (모든 값은 문자열)
    """
    item_ids = [item["item_id"] for item in top_items]
    names = [item["item_name"] for item in top_items]

    return {
        "type": "category",
        "category_name": category_name,
        "item_ids": json.dumps(item_ids, ensure_ascii=False),
        "item_names": json.dumps(names, ensure_ascii=False),
        "count": str(len(top_items)),
        "action": "open_category",
    }


# ---------------------------------------------------------------------------
# Dev mode helpers
# ---------------------------------------------------------------------------


def _log_dev_push(
    *,
    token: str | None = None,
    topic: str | None = None,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> None:
    """개발 모드에서 푸시 알림 내용을 로그로 출력한다.

    Firebase가 초기화되지 않은 환경에서 실제 발송 대신 호출된다.
    """
    target = f"token={token[:20]}..." if token else f"topic={topic}"
    logger.info(
        "[DEV] Push notification (not sent): target=%s, title=%s, body=%s, data=%s",
        target,
        title,
        body,
        json.dumps(data, ensure_ascii=False) if data else "None",
    )
