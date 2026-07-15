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


class Envelope(BaseModel):
    """표준 응답 봉투."""

    status: Literal["success"] = "success"
    data: Any


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    version: str
    cache_records: int = Field(default=0)
