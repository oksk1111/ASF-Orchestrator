"""fresh_alert 웹앱 호환 라우트.

공공 API 연결 없이도 캐시/샘플 데이터를 제공하여 웹앱 개발을 지원한다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Form, Query

from app.cache import store

router = APIRouter(prefix="/api/v1", tags=["FreshAlert"])


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/auth/token")
def get_token(
    username: str = Form(default="dev"),
    password: str = Form(default=""),
) -> dict[str, Any]:
    """개발용 토큰 발급 (항상 성공, 인증 없이 통과)."""
    return {
        "access_token": "dev-sample-token",
        "token_type": "bearer",
        "user_id": f"user_{username}",
    }


# ── Recommendations ───────────────────────────────────────────────────────────

@router.get("/fresh-alert/recommendations/today")
def recommendations_today() -> dict[str, Any]:
    """오늘의 추천 품목 (가격 캐시에서 최신 데이터 기반)."""
    records = store.latest_prices(limit=200)
    seen: dict[str, dict] = {}
    for r in records:
        if r.item_id not in seen:
            seen[r.item_id] = {
                "item_id": r.item_id,
                "item_name": r.item_name,
                "category": r.category,
                "avg_price": r.avg_price,
                "unit": r.unit,
                "sale_date": r.sale_date,
                "market_name": r.market_name,
                "source": r.source,
            }
    recommendations = list(seen.values())[:8]
    return {
        "status": "success",
        "data": {
            "date": _today(),
            "recommendations": recommendations,
        },
    }


# ── Keywords ──────────────────────────────────────────────────────────────────

@router.get("/fresh-alert/keywords")
def get_keywords(user_id: str = Query(default="")) -> dict[str, Any]:
    """사용자 관심 키워드 목록 (샘플)."""
    sample_keywords = ["배추", "사과", "대파", "감자", "고등어", "삼겹살"]
    return {
        "status": "success",
        "data": {
            "user_id": user_id,
            "keywords": [
                {"keyword": kw, "alert_enabled": True, "threshold_pct": 10}
                for kw in sample_keywords
            ],
        },
    }


# ── Seasons ───────────────────────────────────────────────────────────────────

_SEASON_MAP: dict[tuple[int, ...], tuple[str, list[str]]] = {
    (3, 4, 5): ("봄", ["딸기", "봄나물", "냉이", "달래", "쑥"]),
    (6, 7, 8): ("여름", ["수박", "참외", "오이", "복숭아", "토마토"]),
    (9, 10, 11): ("가을", ["사과", "배", "감", "고구마", "밤"]),
    (12, 1, 2): ("겨울", ["귤", "배추", "무", "시금치", "굴"]),
}


@router.get("/fresh-alert/seasons/current")
def current_season() -> dict[str, Any]:
    """현재 제철 품목 목록 (캐시 가격 포함)."""
    month = (datetime.now(timezone.utc) + timedelta(hours=9)).month
    season_name = "여름"
    items: list[str] = ["수박", "참외", "오이"]
    for months, (name, season_items) in _SEASON_MAP.items():
        if month in months:
            season_name = name
            items = season_items
            break

    price_records = store.latest_prices(limit=500)
    price_map = {r.item_name: r.avg_price for r in price_records}

    return {
        "status": "success",
        "data": {
            "season": season_name,
            "items": [
                {
                    "item_name": item,
                    "season": season_name,
                    "avg_price": price_map.get(item, 0),
                    "in_cache": item in price_map,
                }
                for item in items
            ],
        },
    }


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/fresh-alert/notifications")
def get_notifications(
    user_id: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """가격 변동 알림 목록 (캐시 데이터 기반 샘플)."""
    records = store.latest_prices(limit=200)
    notifications = []
    for r in records:
        if r.avg_price == 0:
            continue
        spread = r.max_price - r.min_price
        change_pct = round(spread / r.avg_price * 100, 1)
        if change_pct >= 5:
            notifications.append(
                {
                    "id": f"notif-{r.item_id}-{r.sale_date}",
                    "item_name": r.item_name,
                    "category": r.category,
                    "message": f"{r.item_name} 가격이 {change_pct}% 변동되었습니다",
                    "avg_price": r.avg_price,
                    "change_pct": change_pct,
                    "sale_date": r.sale_date,
                    "market_name": r.market_name,
                    "read": False,
                }
            )
    notifications = notifications[:limit]
    return {
        "status": "success",
        "data": {
            "user_id": user_id,
            "total": len(notifications),
            "notifications": notifications,
        },
    }


# ── Basket Recommendation ──────────────────────────────────────────────────────

@router.get("/recommendation/basket")
def get_recommendation_basket() -> dict[str, Any]:
    """장바구니 추천 목록 (샘플)."""
    return {
        "status": "success",
        "data": {
            "basket": [
                {"item_name": "배추", "category": "채소류", "avg_price": 3000, "recommend_reason": "가격 하락세"},
                {"item_name": "고등어", "category": "수산물", "avg_price": 9000, "recommend_reason": "제철 어종"},
            ]
        }
    }


# ── Pricing Forecast ───────────────────────────────────────────────────────────

@router.get("/forecast/pricing")
def get_forecast_pricing() -> dict[str, Any]:
    """가격 예측 정보 (샘플)."""
    return {
        "status": "success",
        "data": {
            "forecasts": [
                {"item_name": "삼겹살", "trend": "up", "next_week_price": 19000},
                {"item_name": "상추", "trend": "down", "next_week_price": 2800},
            ]
        }
    }


# ── Logistics Route ────────────────────────────────────────────────────────────

@router.post("/logistics/route")
def post_logistics_route() -> dict[str, Any]:
    """물류/배송 경로 계산 (샘플)."""
    return {
        "status": "success",
        "data": {
            "route_id": "rt-local-999",
            "estimated_time_mins": 45,
            "distance_km": 12.5,
            "message": "최적 경로가 계산되었습니다."
        }
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _today() -> str:
    kst = datetime.now(timezone.utc) + timedelta(hours=9)
    return kst.strftime("%Y-%m-%d")
