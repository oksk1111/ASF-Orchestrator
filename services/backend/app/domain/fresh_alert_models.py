from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Item(BaseModel):
    item_id: str
    large_code: str
    mid_code: str
    small_code: str = ""
    large_name: str
    mid_name: str
    small_name: str = ""
    season_start: int | None = None
    season_end: int | None = None


class PriceRecord(BaseModel):
    item_id: str
    market_code: str
    market_name: str
    sale_date: str
    avg_price: int
    min_price: int
    max_price: int
    total_qty: int
    total_amt: int
    data_source: Literal["MAFRA", "KAMIS"]


class RealtimeAuction(BaseModel):
    item_id: str
    market_code: str
    market_name: str
    auction_date: str
    auction_time: str
    cost: int
    qty: int
    grade: str
    origin: str


class DailyAnalysis(BaseModel):
    item_id: str
    analysis_date: str
    avg_30d: int
    current_price: int
    price_drop_rate: float
    qty_increase_rate: float
    is_season: bool
    recommend_score: float = Field(ge=0.0, le=1.0)


class KeywordSubscription(BaseModel):
    id: str
    user_id: str
    item_id: str
    item_name: str
    threshold_type: Literal["percentage", "absolute"]
    threshold_value: float
    enabled: bool = True


class CategorySubscription(BaseModel):
    id: str
    user_id: str
    large_code: str
    large_name: str
    mid_code: str | None = None
    mid_name: str | None = None
    notify_days: list[str] = Field(default_factory=lambda: ["MON", "THU"])
    enabled: bool = True


class Notification(BaseModel):
    id: str
    user_id: str
    type: Literal["recommend", "keyword", "category"]
    title: str
    body: str
    item_id: str | None = None
    sent_at: str
    read_at: str | None = None


class RecommendationItem(BaseModel):
    rank: int
    item_id: str
    item_name: str
    large_name: str
    current_price: int
    avg_30d: int
    price_drop_rate: float
    is_season: bool
    recommend_score: float = Field(ge=0.0, le=1.0)


class DailyRecommendation(BaseModel):
    date: str
    items: list[RecommendationItem]


class SeasonCalendarEntry(BaseModel):
    month: int = Field(ge=1, le=12)
    vegetables: list[str] = Field(default_factory=list)
    fruits: list[str] = Field(default_factory=list)
    seafood: list[str] = Field(default_factory=list)


# --- Request / Response envelopes ---


class KeywordCreateRequest(BaseModel):
    item_id: str
    item_name: str
    threshold_type: Literal["percentage", "absolute"]
    threshold_value: float


class KeywordUpdateRequest(BaseModel):
    threshold_type: str | None = None
    threshold_value: float | None = None
    enabled: bool | None = None


class CategorySubscribeRequest(BaseModel):
    large_code: str
    large_name: str
    mid_code: str | None = None
    mid_name: str | None = None
    notify_days: list[str] | None = None


class FreshAlertEnvelope(BaseModel):
    status: Literal["success"] = "success"
    data: Any


class PriceHistoryResponse(BaseModel):
    item_id: str
    item_name: str
    market_code: str
    prices: list[PriceRecord]


class MarketComparisonItem(BaseModel):
    market_code: str
    market_name: str
    avg_price: int
    price_drop_rate: float


class MarketComparisonResponse(BaseModel):
    item_id: str
    item_name: str
    date: str
    markets: list[MarketComparisonItem]
