"""FreshAlert 알림 서비스.

추천/키워드/카테고리 알림을 생성하고 발송하는 서비스 레이어.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)


def generate_recommend_notification(
    items: list[dict],
    date: str,
) -> dict:
    """오늘의 추천 알림 메시지를 생성한다.

    Args:
        items: 추천 품목 리스트 (rank, item_name, price_drop_rate, is_season)
        date: 추천 날짜 (YYYYMMDD)

    Returns:
        알림 dict (title, body)
    """
    if not items:
        return {
            "title": "🥬 오늘의 추천이 없습니다",
            "body": "현재 가격 변동이 크지 않아요. 내일 다시 확인해보세요!",
        }

    top_items_text = ", ".join(
        f"{item['item_name']}({item['price_drop_rate']:+.0f}%)"
        for item in items[:3]
    )

    season_count = sum(1 for item in items if item.get("is_season"))
    season_text = f" 제철 {season_count}종 포함!" if season_count > 0 else ""

    return {
        "title": f"🥬 오늘의 추천 {len(items)}종이 도착했어요!",
        "body": f"{top_items_text}...{season_text} 지금 확인해보세요",
    }


def generate_keyword_notification(
    item_name: str,
    current_price: int,
    avg_30d: float,
    price_drop_rate: float,
) -> dict:
    """키워드 알림 메시지를 생성한다.

    Args:
        item_name: 품목명
        current_price: 현재가
        avg_30d: 30일 평균가
        price_drop_rate: 하락률

    Returns:
        알림 dict (title, body)
    """
    emoji_map = {
        "딸기": "🍓", "사과": "🍎", "수박": "🍉", "포도": "🍇",
        "복숭아": "🍑", "귤": "🍊", "배추": "🥬", "토마토": "🍅",
        "오이": "🥒", "당근": "🥕", "양파": "🧅", "고구마": "🍠",
        "옥수수": "🌽", "고추": "🌶️",
    }
    emoji = emoji_map.get(item_name, "🛒")

    price_formatted = f"{current_price:,}"
    return {
        "title": f"{emoji} {item_name}가 목표 가격에 도달했어요!",
        "body": (
            f"현재 {price_formatted}원/kg "
            f"(평균 대비 {price_drop_rate:+.1f}%) — 지금이 구매 적기!"
        ),
    }


def generate_category_notification(
    category_name: str,
    top_items: list[dict],
) -> dict:
    """카테고리 알림 메시지를 생성한다.

    Args:
        category_name: 카테고리명 (예: "과일류")
        top_items: 해당 카테고리 추천 품목 리스트

    Returns:
        알림 dict (title, body)
    """
    category_emoji = {
        "채소류": "🥗", "과일류": "🍎", "수산물": "🐟", "축산물": "🥩",
    }
    emoji = category_emoji.get(category_name, "📦")

    if not top_items:
        return {
            "title": f"{emoji} {category_name} 이번 주 현황",
            "body": "특별한 가격 변동이 없습니다.",
        }

    items_text = ", ".join(
        f"{item['item_name']}({item['price_drop_rate']:+.0f}%)"
        for item in top_items[:3]
    )

    return {
        "title": f"{emoji} {category_name} 이번 주 BEST {min(3, len(top_items))}",
        "body": f"{items_text} — 가격 대폭 하락!",
    }


def create_notification(
    user_id: str,
    notif_type: str,
    title: str,
    body: str,
    item_id: str | None = None,
) -> dict:
    """알림 객체를 생성한다.

    Args:
        user_id: 사용자 ID
        notif_type: 알림 유형 ("recommend" | "keyword" | "category")
        title: 알림 제목
        body: 알림 본문
        item_id: 관련 품목 ID (선택)

    Returns:
        Notification dict
    """
    return {
        "id": str(uuid4()),
        "user_id": user_id,
        "type": notif_type,
        "title": title,
        "body": body,
        "item_id": item_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "read_at": None,
    }


async def send_push_notification(
    push_token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """푸시 알림을 발송한다 (FCM).

    현재는 로깅만 수행. 추후 Firebase Admin SDK 연동.

    Args:
        push_token: FCM 디바이스 토큰
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 페이로드

    Returns:
        발송 성공 여부
    """
    # TODO: Firebase Admin SDK 연동
    logger.info(
        "Push notification sent: token=%s, title=%s",
        push_token[:20] + "..." if push_token else "N/A",
        title,
    )
    return True
