"""정규화된 데이터 스키마.

서로 다른 공공 포털(MAFRA, KAMIS)의 응답을 내부 표준 스키마로 통일한다.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Source = Literal["MAFRA", "KAMIS", "SAMPLE"]


class PriceRecord(BaseModel):
    """정규화된 가격 레코드."""

    source: Source
    item_id: str
    item_name: str
    category: str = ""
    market_code: str = ""
    market_name: str = ""
    sale_date: str  # YYYYMMDD
    unit: str = ""
    avg_price: int = 0
    min_price: int = 0
    max_price: int = 0
    collected_at: str = ""


class PriceAlert(BaseModel):
    """가격 알람 등록 정보."""

    id: int | None = None
    user_id: str
    item_id: str
    item_name: str = ""
    target_price: int
    direction: Literal["above", "below"]
    active: bool = True
    created_at: str = ""


class AlertTrigger(BaseModel):
    """가격 알람 트리거 기록."""

    id: int | None = None
    alert_id: int
    user_id: str
    item_id: str
    item_name: str = ""
    target_price: int
    actual_price: int
    direction: str
    triggered_at: str
    pushed_at: str | None = None
    read_at: str | None = None


class CollectionLog(BaseModel):
    """수집 실행 로그."""

    id: int | None = None
    source: str
    status: Literal["success", "error", "running"]
    fetched: int = 0
    saved: int = 0
    message: str = ""
    started_at: str
    finished_at: str | None = None


class SourceSummary(BaseModel):
    """소스별 캐시 요약."""

    source: str
    record_count: int = 0
    latest_sale_date: str | None = None
    last_collected_at: str | None = None


class User(BaseModel):
    """사용자 정보."""

    id: int | None = None
    google_id: str = ""
    email: str = ""
    name: str = ""
    profile_image: str = ""
    role: Literal["user", "admin"] = "user"
    is_active: bool = True
    created_at: str = ""
    last_login_at: str | None = None


class GoogleLoginRequest(BaseModel):
    """Google OAuth 로그인 요청."""

    id_token: str


class AuthResponse(BaseModel):
    """인증 응답."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 30 * 24 * 3600
    user: User


class UserDevice(BaseModel):
    """사용자 디바이스(FCM 토큰) 정보."""

    id: int | None = None
    user_id: str
    fcm_token: str
    device_name: str = ""
    platform: str = ""  # "ios" / "android" / "web"
    created_at: str = ""
    updated_at: str = ""


class DeviceRegisterRequest(BaseModel):
    """디바이스 FCM 토큰 등록 요청."""

    fcm_token: str
    device_name: str = ""
    platform: str = ""


class ActivityLog(BaseModel):
    """사용자 활동 로그."""

    id: int | None = None
    user_id: str = ""
    user_email: str = ""
    action: str = ""
    detail: str = ""
    ip_address: str = ""
    user_agent: str = ""
    created_at: str = ""


class CatalogItem(BaseModel):
    """KAMIS 아이템 카탈로그 엔트리."""

    id: int | None = None
    source: str = "KAMIS"
    item_code: str
    item_name: str
    kind_code: str = ""
    kind_name: str = ""
    rank_code: str = ""
    rank_name: str = ""
    category_code: str
    category_name: str = ""
    unit: str = ""
    canonical_id: str = ""
    latest_price: int = 0
    price_change_rate: float = 0.0
    price_direction: str = ""
    updated_at: str = ""


class Envelope(BaseModel):
    """표준 응답 봉투."""

    status: Literal["success"] = "success"
    data: Any


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    version: str
    cache_records: int = Field(default=0)
