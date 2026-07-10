"""FreshAlert API 라우트.

제철 농식품 가격 알림 서비스의 REST API 엔드포인트.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from app.domain.fresh_alert_models import (
    CategorySubscribeRequest,
    CategorySubscription,
    DailyRecommendation,
    FreshAlertEnvelope,
    KeywordCreateRequest,
    KeywordSubscription,
    KeywordUpdateRequest,
    MarketComparisonItem,
    MarketComparisonResponse,
    Notification,
    PriceHistoryResponse,
    SeasonCalendarEntry,
)
from app.services.fresh_alert.analyzer import (
    calculate_moving_average,
    calculate_price_drop_rate,
    calculate_recommend_score,
    calculate_qty_increase_rate,
    check_keyword_trigger,
    is_in_season,
    select_top_recommendations,
)
from app.services.fresh_alert.repository import fresh_alert_repo
from app.services.fresh_alert.season_data import MARKET_CODES, SEASON_CALENDAR

router = APIRouter(prefix="/fresh-alert", tags=["FreshAlert"])


# ─── 추천 ────────────────────────────────────────────────────────────────────


@router.get("/recommendations/today")
def get_today_recommendations() -> FreshAlertEnvelope:
    """오늘의 추천 TOP 5를 반환한다."""
    rec = fresh_alert_repo.get_latest_recommendation()
    if rec is None:
        # 추천이 아직 없으면 실시간 계산
        rec = _compute_recommendations()
    return FreshAlertEnvelope(data=rec)


@router.get("/recommendations/history")
def get_recommendation_history(
    limit: int = Query(default=7, ge=1, le=30),
) -> FreshAlertEnvelope:
    """과거 추천 이력을 반환한다."""
    # 현재는 최근 추천 하나만 반환 (추후 히스토리 구현)
    rec = fresh_alert_repo.get_latest_recommendation()
    data = [rec] if rec else []
    return FreshAlertEnvelope(data=data)


# ─── 품목 ────────────────────────────────────────────────────────────────────


@router.get("/items/search")
def search_items(
    q: str = Query(min_length=1, description="검색어"),
) -> FreshAlertEnvelope:
    """품목을 검색한다 (자동완성)."""
    items = fresh_alert_repo.search_items(q)
    return FreshAlertEnvelope(data=items)


@router.get("/items/{item_id}")
def get_item_detail(item_id: str) -> FreshAlertEnvelope:
    """품목 상세 정보를 반환한다."""
    item = fresh_alert_repo.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다")

    # 가격 이력에서 현재가 및 분석 데이터 계산
    history = fresh_alert_repo.get_price_history(item_id, days=30)
    prices = [r.avg_price for r in history]
    avg_30d = calculate_moving_average(prices) if prices else 0
    current_price = prices[-1] if prices else 0
    price_drop = calculate_price_drop_rate(current_price, avg_30d)

    now_month = datetime.now(timezone.utc).month
    season = is_in_season(now_month, item.season_start, item.season_end)

    return FreshAlertEnvelope(data={
        "item": item,
        "current_price": current_price,
        "avg_30d": int(avg_30d),
        "price_drop_rate": price_drop,
        "is_season": season,
        "price_history_count": len(history),
    })


@router.get("/items/{item_id}/prices")
def get_item_prices(
    item_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> FreshAlertEnvelope:
    """품목의 가격 추이를 반환한다."""
    item = fresh_alert_repo.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다")

    history = fresh_alert_repo.get_price_history(item_id, days=days)
    response = PriceHistoryResponse(
        item_id=item_id,
        item_name=item.mid_name,
        market_code="ALL",
        prices=history,
    )
    return FreshAlertEnvelope(data=response)


@router.get("/items/{item_id}/markets")
def get_item_market_comparison(item_id: str) -> FreshAlertEnvelope:
    """시장별 가격 비교를 반환한다."""
    item = fresh_alert_repo.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다")

    history = fresh_alert_repo.get_price_history(item_id, days=30)
    prices = [r.avg_price for r in history]
    avg_30d = calculate_moving_average(prices)

    # 시장별로 최근 가격 그룹핑
    market_prices: dict[str, list[int]] = {}
    for record in history:
        market_prices.setdefault(record.market_code, []).append(record.avg_price)

    markets = []
    for code, mp in market_prices.items():
        market_avg = sum(mp[-5:]) / len(mp[-5:]) if mp else 0
        drop = calculate_price_drop_rate(int(market_avg), avg_30d)
        markets.append(MarketComparisonItem(
            market_code=code,
            market_name=MARKET_CODES.get(code, code),
            avg_price=int(market_avg),
            price_drop_rate=drop,
        ))

    markets.sort(key=lambda m: m.avg_price)

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    response = MarketComparisonResponse(
        item_id=item_id,
        item_name=item.mid_name,
        date=today_str,
        markets=markets,
    )
    return FreshAlertEnvelope(data=response)


# ─── 키워드 구독 ────────────────────────────────────────────────────────────


@router.get("/keywords")
def get_keywords(
    user_id: str = Query(default="user_dev_01"),
) -> FreshAlertEnvelope:
    """사용자의 키워드 구독 목록을 반환한다."""
    subs = fresh_alert_repo.get_keyword_subscriptions(user_id)
    return FreshAlertEnvelope(data=subs)


@router.post("/keywords", status_code=201)
def create_keyword(
    request: KeywordCreateRequest,
    user_id: str = Query(default="user_dev_01"),
) -> FreshAlertEnvelope:
    """키워드를 등록한다."""
    # 품목 존재 확인
    item = fresh_alert_repo.get_item(request.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다")

    # 중복 확인
    existing = fresh_alert_repo.get_keyword_subscriptions(user_id)
    if any(s.item_id == request.item_id for s in existing):
        raise HTTPException(status_code=409, detail="이미 등록된 키워드입니다")

    # 최대 20개 제한
    if len(existing) >= 20:
        raise HTTPException(status_code=400, detail="키워드는 최대 20개까지 등록 가능합니다")

    sub = KeywordSubscription(
        id=str(uuid4()),
        user_id=user_id,
        item_id=request.item_id,
        item_name=request.item_name,
        threshold_type=request.threshold_type,
        threshold_value=request.threshold_value,
        enabled=True,
    )
    fresh_alert_repo.add_keyword_subscription(user_id, sub)
    return FreshAlertEnvelope(data=sub)


@router.put("/keywords/{keyword_id}")
def update_keyword(
    keyword_id: str,
    request: KeywordUpdateRequest,
    user_id: str = Query(default="user_dev_01"),
) -> FreshAlertEnvelope:
    """키워드 구독 설정을 수정한다."""
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="수정할 항목이 없습니다")

    result = fresh_alert_repo.update_keyword_subscription(user_id, keyword_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다")
    return FreshAlertEnvelope(data=result)


@router.delete("/keywords/{keyword_id}")
def delete_keyword(
    keyword_id: str,
    user_id: str = Query(default="user_dev_01"),
) -> FreshAlertEnvelope:
    """키워드를 삭제한다."""
    success = fresh_alert_repo.delete_keyword_subscription(user_id, keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다")
    return FreshAlertEnvelope(data={"deleted": keyword_id})


# ─── 카테고리 구독 ──────────────────────────────────────────────────────────


@router.get("/categories")
def get_all_categories() -> FreshAlertEnvelope:
    """전체 카테고리 목록을 반환한다."""
    from app.services.fresh_alert.season_data import LARGE_CATEGORIES, MID_CATEGORIES

    result = []
    for code, name in LARGE_CATEGORIES.items():
        mid_list = [
            {"code": mc, "name": mn}
            for mc, mn in MID_CATEGORIES.get(code, {}).items()
        ]
        result.append({
            "large_code": code,
            "large_name": name,
            "mid_categories": mid_list,
        })
    return FreshAlertEnvelope(data=result)


@router.get("/categories/subscribed")
def get_subscribed_categories(
    user_id: str = Query(default="user_dev_01"),
) -> FreshAlertEnvelope:
    """사용자의 카테고리 구독 목록을 반환한다."""
    subs = fresh_alert_repo.get_category_subscriptions(user_id)
    return FreshAlertEnvelope(data=subs)


@router.post("/categories/subscribe", status_code=201)
def subscribe_category(
    request: CategorySubscribeRequest,
    user_id: str = Query(default="user_dev_01"),
) -> FreshAlertEnvelope:
    """카테고리를 구독한다."""
    sub = CategorySubscription(
        id=str(uuid4()),
        user_id=user_id,
        large_code=request.large_code,
        large_name=request.large_name,
        mid_code=request.mid_code,
        mid_name=request.mid_name,
        notify_days=request.notify_days or ["MON", "THU"],
        enabled=True,
    )
    fresh_alert_repo.add_category_subscription(user_id, sub)
    return FreshAlertEnvelope(data=sub)


@router.delete("/categories/subscribe/{sub_id}")
def unsubscribe_category(
    sub_id: str,
    user_id: str = Query(default="user_dev_01"),
) -> FreshAlertEnvelope:
    """카테고리 구독을 해제한다."""
    success = fresh_alert_repo.delete_category_subscription(user_id, sub_id)
    if not success:
        raise HTTPException(status_code=404, detail="구독을 찾을 수 없습니다")
    return FreshAlertEnvelope(data={"deleted": sub_id})


# ─── 알림 ────────────────────────────────────────────────────────────────────


@router.get("/notifications")
def get_notifications(
    user_id: str = Query(default="user_dev_01"),
    limit: int = Query(default=50, ge=1, le=200),
) -> FreshAlertEnvelope:
    """알림 이력을 반환한다."""
    notifs = fresh_alert_repo.get_notifications(user_id, limit=limit)
    return FreshAlertEnvelope(data=notifs)


@router.put("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: str,
    user_id: str = Query(default="user_dev_01"),
) -> FreshAlertEnvelope:
    """알림을 읽음 처리한다."""
    success = fresh_alert_repo.mark_notification_read(user_id, notif_id)
    if not success:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
    return FreshAlertEnvelope(data={"read": notif_id})


# ─── 제철 정보 ──────────────────────────────────────────────────────────────


@router.get("/seasons/current")
def get_current_season() -> FreshAlertEnvelope:
    """현재 제철 품목을 반환한다."""
    month = datetime.now(timezone.utc).month
    season = SEASON_CALENDAR.get(month, {})
    return FreshAlertEnvelope(data={
        "month": month,
        "vegetables": season.get("vegetables", []),
        "fruits": season.get("fruits", []),
        "seafood": season.get("seafood", []),
    })


@router.get("/seasons/calendar")
def get_season_calendar() -> FreshAlertEnvelope:
    """월별 제철 캘린더를 반환한다."""
    calendar = [
        SeasonCalendarEntry(
            month=month,
            vegetables=data.get("vegetables", []),
            fruits=data.get("fruits", []),
            seafood=data.get("seafood", []),
        )
        for month, data in sorted(SEASON_CALENDAR.items())
    ]
    return FreshAlertEnvelope(data=calendar)


# ─── 내부 헬퍼 ──────────────────────────────────────────────────────────────


def _compute_recommendations() -> DailyRecommendation:
    """실시간으로 추천 목록을 계산한다."""
    from app.domain.fresh_alert_models import RecommendationItem

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y%m%d")
    month = now.month

    items = fresh_alert_repo.list_items()
    analyses = []

    for item in items:
        history = fresh_alert_repo.get_price_history(item.item_id, days=30)
        if not history:
            continue

        prices = [r.avg_price for r in history]
        qtys = [r.total_qty for r in history]

        avg_30d = calculate_moving_average(prices, 30)
        avg_7d_qty = calculate_moving_average(qtys, 7)
        current_price = prices[-1]
        current_qty = qtys[-1] if qtys else 0

        price_drop = calculate_price_drop_rate(current_price, avg_30d)
        qty_increase = calculate_qty_increase_rate(current_qty, avg_7d_qty)
        season = is_in_season(month, item.season_start, item.season_end)
        score = calculate_recommend_score(price_drop, qty_increase, season)

        analyses.append({
            "item_id": item.item_id,
            "item_name": item.mid_name or item.large_name,
            "large_name": item.large_name,
            "current_price": current_price,
            "avg_30d": int(avg_30d),
            "price_drop_rate": price_drop,
            "qty_increase_rate": qty_increase,
            "is_season": season,
            "recommend_score": score,
        })

    top = select_top_recommendations(analyses, top_n=5)

    rec_items = [
        RecommendationItem(
            rank=i + 1,
            item_id=item["item_id"],
            item_name=item["item_name"],
            large_name=item["large_name"],
            current_price=item["current_price"],
            avg_30d=item["avg_30d"],
            price_drop_rate=item["price_drop_rate"],
            is_season=item["is_season"],
            recommend_score=item["recommend_score"],
        )
        for i, item in enumerate(top)
    ]

    recommendation = DailyRecommendation(date=today_str, items=rec_items)
    fresh_alert_repo.save_recommendation(recommendation)
    return recommendation
