"""능동적 가격 알람 체커.

수집(ingest) 완료 후 자동 호출되어 모든 활성 알람을 검사하고,
조건 충족 시 트리거 레코드를 생성하고 FCM push를 발송한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.cache import store
from app.services.push_notification import send_price_alert_push

logger = logging.getLogger(__name__)


async def check_and_trigger_alerts() -> int:
    """모든 활성 알람을 검사하여 조건 충족 시 트리거를 생성한다.

    Returns:
        새로 트리거된 알람 수.
    """
    active_alerts = store.get_all_active_alerts()
    if not active_alerts:
        return 0

    triggered_count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for alert in active_alerts:
        current_price = store.latest_price_for_item(alert.item_id)
        if current_price is None or current_price == 0:
            continue

        # 트리거 조건 판정
        should_trigger = False
        if alert.direction == "above" and current_price >= alert.target_price:
            should_trigger = True
        elif alert.direction == "below" and current_price <= alert.target_price:
            should_trigger = True

        if not should_trigger:
            continue

        # 오늘 이미 트리거된 적 있는지 확인 (중복 방지)
        if store.alert_triggered_today(alert.id):
            continue

        # 트리거 레코드 생성
        store.create_alert_trigger(
            alert_id=alert.id,
            user_id=alert.user_id,
            item_id=alert.item_id,
            item_name=alert.item_name,
            target_price=alert.target_price,
            actual_price=current_price,
            direction=alert.direction,
            triggered_at=now_iso,
        )
        triggered_count += 1

        # FCM Push 발송
        device_tokens = store.get_user_device_tokens(alert.user_id)
        if device_tokens:
            try:
                await send_price_alert_push(
                    device_tokens=device_tokens,
                    item_name=alert.item_name or alert.item_id,
                    target_price=alert.target_price,
                    actual_price=current_price,
                    direction=alert.direction,
                )
            except Exception as exc:
                logger.warning("알람 %d push 발송 실패: %s", alert.id, exc)

    if triggered_count:
        logger.info("알람 체크 완료: %d건 새로 트리거됨", triggered_count)
    return triggered_count
