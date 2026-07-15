"""가격 알람 API.

fresh_alert 앱의 품목 상세화면에서 "이 가격이 되면 알려줘" 버튼이 호출하는
등록/조회/삭제 API. 별도 로그인 시스템이 없으므로 클라이언트가 보내는
user_id(기기/사용자 식별자) 기준으로 알람을 구분한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.cache import store
from app.core.security import require_consumer
from app.models.schemas import Envelope, PriceAlert

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"], dependencies=[Depends(require_consumer)])


@router.post("")
def create_alert(alert: PriceAlert) -> Envelope:
    """가격 알람을 등록한다.

    Body 예: {"user_id": "device-abc", "item_id": "KAMIS-200-211-01-04",
              "item_name": "배추", "target_price": 5000, "direction": "below"}
    """
    if alert.target_price <= 0:
        raise HTTPException(status_code=422, detail="target_price는 0보다 커야 합니다")
    created = store.create_alert(alert)
    return Envelope(data=created)


@router.get("")
def list_alerts(user_id: str = Query(..., description="사용자/기기 식별자")) -> Envelope:
    """사용자의 가격 알람 목록을 반환한다. 각 알람에 현재가/트리거 여부를 포함."""
    alerts = store.list_alerts(user_id)
    data = []
    for a in alerts:
        current_price = store.latest_price_for_item(a.item_id)
        triggered = False
        if a.active and current_price:
            triggered = (
                current_price >= a.target_price
                if a.direction == "above"
                else current_price <= a.target_price
            )
        data.append({
            **a.model_dump(),
            "current_price": current_price,
            "triggered": triggered,
        })
    return Envelope(data=data)


@router.delete("/{alert_id}")
def delete_alert(alert_id: int, user_id: str = Query(..., description="사용자/기기 식별자")) -> Envelope:
    """본인 소유의 가격 알람을 삭제한다."""
    deleted = store.delete_alert(alert_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="알람을 찾을 수 없습니다")
    return Envelope(data={"id": alert_id, "deleted": True})
