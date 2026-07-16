"""가격 알람 API.

fresh_alert 앱의 품목 상세화면에서 "이 가격이 되면 알려줘" 버튼이 호출하는
등록/조회/삭제 API + 트리거된 알람 조회 + FCM 디바이스 관리.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.cache import store
from app.core.security import require_consumer
from app.models.schemas import DeviceRegisterRequest, Envelope, PriceAlert

router = APIRouter(prefix="/api/v1", tags=["Alerts"], dependencies=[Depends(require_consumer)])


# ─── 알람 CRUD ────────────────────────────────────────────────────────────────


@router.post("/alerts")
def create_alert(alert: PriceAlert) -> Envelope:
    """가격 알람을 등록한다.

    Body 예: {"user_id": "device-abc", "item_id": "KAMIS-200-211-01-04",
              "item_name": "배추", "target_price": 5000, "direction": "below"}
    """
    if alert.target_price <= 0:
        raise HTTPException(status_code=422, detail="target_price는 0보다 커야 합니다")
    created = store.create_alert(alert)
    return Envelope(data=created)


@router.get("/alerts")
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


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, user_id: str = Query(..., description="사용자/기기 식별자")) -> Envelope:
    """본인 소유의 가격 알람을 삭제한다."""
    deleted = store.delete_alert(alert_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="알람을 찾을 수 없습니다")
    return Envelope(data={"id": alert_id, "deleted": True})


# ─── 트리거된 알람 ────────────────────────────────────────────────────────────


@router.get("/alerts/triggered")
def get_triggered_alerts(
    user_id: str = Query(..., description="사용자/기기 식별자"),
    since: str | None = Query(default=None, description="ISO timestamp — 이후 트리거만 반환"),
    unread_only: bool = Query(default=False, description="읽지 않은 것만"),
    limit: int = Query(default=50, ge=1, le=200),
) -> Envelope:
    """트리거된 알람 이력을 반환한다. 프론트엔드가 주기적으로 폴링한다."""
    triggers = store.list_triggered_alerts(
        user_id=user_id, since=since, unread_only=unread_only, limit=limit
    )
    return Envelope(data=triggers)


@router.post("/alerts/triggered/{trigger_id}/read")
def mark_trigger_read(
    trigger_id: int,
    user_id: str = Query(..., description="사용자/기기 식별자"),
) -> Envelope:
    """트리거된 알람을 읽음 처리한다."""
    success = store.mark_trigger_read(trigger_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="트리거를 찾을 수 없습니다")
    return Envelope(data={"id": trigger_id, "read": True})


# ─── 디바이스 관리 (FCM 토큰) ─────────────────────────────────────────────────


@router.post("/devices")
def register_device(
    req: DeviceRegisterRequest,
    user_id: str = Query(..., description="사용자/기기 식별자"),
) -> Envelope:
    """FCM 디바이스 토큰을 등록/갱신한다."""
    if not req.fcm_token:
        raise HTTPException(status_code=422, detail="fcm_token은 필수입니다")
    device_id = store.register_device(
        user_id=user_id,
        fcm_token=req.fcm_token,
        device_name=req.device_name,
        platform=req.platform,
    )
    return Envelope(data={"id": device_id, "registered": True})


@router.delete("/devices/{fcm_token}")
def remove_device(
    fcm_token: str,
    user_id: str = Query(..., description="사용자/기기 식별자"),
) -> Envelope:
    """FCM 디바이스 토큰을 제거한다 (로그아웃 시)."""
    removed = store.remove_device(user_id=user_id, fcm_token=fcm_token)
    if not removed:
        raise HTTPException(status_code=404, detail="디바이스를 찾을 수 없습니다")
    return Envelope(data={"fcm_token": fcm_token, "removed": True})
