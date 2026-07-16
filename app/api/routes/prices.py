"""소비자용 가격 데이터 라우트.

fresh_alert 앱이 공공 포털 대신 호출하는 정규화 API.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query

from app.cache import store
from app.collectors.base import CollectorError
from app.core.config import settings
from app.core.security import require_consumer
from app.models.schemas import Envelope
from app.services import history

router = APIRouter(prefix="/api/v1", tags=["Prices"], dependencies=[Depends(require_consumer)])


@router.get("/prices")
def get_prices(
    item_id: str | None = Query(default=None, description="품목 ID 필터"),
    source: str | None = Query(default=None, description="소스 필터 (MAFRA/KAMIS/SAMPLE)"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> Envelope:
    """정규화된 가격 레코드를 최신순으로 반환한다."""
    records = store.query_prices(item_id=item_id, source=source, limit=limit)
    return Envelope(data=records)


@router.get("/prices/latest")
def get_latest_prices(limit: int = Query(default=50, ge=1, le=500)) -> Envelope:
    """가장 최근 수집된 레코드를 반환한다."""
    return Envelope(data=store.latest_prices(limit=limit))


@router.get("/items")
def get_items() -> Envelope:
    """캐시에 존재하는 고유 품목 목록을 반환한다."""
    records = store.query_prices(limit=1000)
    seen: dict[str, dict] = {}
    for r in records:
        if r.item_id not in seen:
            seen[r.item_id] = {
                "item_id": r.item_id,
                "item_name": r.item_name,
                "category": r.category,
            }
    return Envelope(data=list(seen.values()))


@router.get("/items/catalog")
def get_item_catalog(
    category: str | None = Query(default=None, description="카테고리 코드 (100~600)"),
    search: str | None = Query(default=None, description="품목명 검색"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> Envelope:
    """KAMIS 전체 아이템 카탈로그를 반환한다."""
    items = store.query_catalog(category_code=category, search=search, limit=limit, offset=offset)
    total = store.count_catalog()
    return Envelope(data={"items": items, "total": total, "limit": limit, "offset": offset})


@router.get("/categories")
def get_categories() -> Envelope:
    """품목 카테고리 목록을 반환한다."""
    categories = [
        {"code": "100", "name": "식량작물"},
        {"code": "200", "name": "채소류"},
        {"code": "300", "name": "특용작물"},
        {"code": "400", "name": "과일류"},
        {"code": "500", "name": "축산물"},
        {"code": "600", "name": "수산물"},
    ]
    return Envelope(data=categories)


@router.get("/items/{item_id}/history")
async def get_item_history(
    item_id: str,
    days: int = Query(default=30, ge=1, le=365, description="조회 기간(일)"),
) -> Envelope:
    """품목 상세화면용 기간별 가격 시계열 + 등락률을 반환한다.

    - series: [{date, price}, ...] 그래프용 시계열
    - normal_series: 평년(과거 평균) 비교선 (KAMIS 품목만 제공, 없으면 빈 배열)
    - change_rate_1d / change_rate_period: 전일 대비 / 조회 기간 시작 대비 등락률(%)
    """
    try:
        return Envelope(data=await history.get_item_history(item_id, days=days))
    except CollectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/items/{item_id}/trend")
async def get_item_trend(
    item_id: str,
    period: str = Query(default="recent", description="recent/monthly/yearly"),
) -> Envelope:
    """품목의 가격 추세 데이터를 반환한다.

    - recent: 최근 40일 추세 (10일 간격)
    - monthly: 월별 평균 추세
    - yearly: 연도별 평균 추세
    """
    from app.collectors.kamis_trend import KamisTrendCollector

    if not settings.kamis_cert_key:
        raise HTTPException(status_code=503, detail="KAMIS API 키가 설정되지 않았습니다")

    # item_id에서 product_no 추출 (KAMIS-{cat}-{item_code}-{kind}-{rank} → item_code)
    parts = item_id.split("-")
    if len(parts) >= 3:
        product_no = parts[2]
    else:
        product_no = item_id

    collector = KamisTrendCollector(settings.kamis_cert_key, settings.kamis_cert_id)
    try:
        if period == "monthly":
            data = await collector.get_monthly_trend(product_no)
        elif period == "yearly":
            data = await collector.get_yearly_trend(product_no)
        else:
            data = await collector.get_recent_trend(product_no)
        return Envelope(data=data)
    except CollectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/items/{item_id}/regional")
async def get_item_regional(item_id: str) -> Envelope:
    """품목의 지역별 가격 비교 데이터를 반환한다."""
    from app.collectors.kamis_regional import KamisRegionalCollector

    if not settings.kamis_cert_key:
        raise HTTPException(status_code=503, detail="KAMIS API 키가 설정되지 않았습니다")

    parts = item_id.split("-")
    if len(parts) >= 3:
        item_code = parts[2]
        category_code = parts[1] if len(parts) >= 2 else ""
        kind_code = parts[3] if len(parts) >= 4 else ""
        rank_code = parts[4] if len(parts) >= 5 else ""
    else:
        item_code = item_id
        category_code = ""
        kind_code = ""
        rank_code = ""

    collector = KamisRegionalCollector(settings.kamis_cert_key, settings.kamis_cert_id)
    try:
        data = await collector.get_item_regional(
            item_code=item_code,
            kind_code=kind_code,
            rank_code=rank_code,
            category_code=category_code,
        )
        return Envelope(data=data)
    except CollectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/sources")
def get_sources() -> Envelope:
    """소스별 캐시 요약을 반환한다."""
    return Envelope(data=store.source_summaries())


@router.get("/recommendations/today")
def get_recommendations(top_n: int = Query(default=10, ge=1, le=50)) -> Envelope:
    """캐시 데이터로부터 간단한 추천(가격 하락 폭 기준)을 계산한다."""
    records = store.query_prices(limit=2000)
    by_item: dict[str, list] = defaultdict(list)
    for r in records:
        by_item[r.item_id].append(r)

    results = []
    for item_id, recs in by_item.items():
        recs.sort(key=lambda x: x.sale_date)
        latest_date = recs[-1].sale_date
        latest = [x.avg_price for x in recs if x.sale_date == latest_date and x.avg_price > 0]
        hist = [x.avg_price for x in recs if x.avg_price > 0]
        if not latest or not hist:
            continue
        latest_avg = sum(latest) / len(latest)
        hist_avg = sum(hist) / len(hist)
        drop = (latest_avg - hist_avg) / hist_avg * 100 if hist_avg else 0.0
        results.append({
            "item_id": item_id,
            "item_name": recs[-1].item_name,
            "category": recs[-1].category,
            "current_price": int(latest_avg),
            "avg_price": int(hist_avg),
            "price_drop_rate": round(drop, 1),
        })

    results.sort(key=lambda x: x["price_drop_rate"])
    return Envelope(data=results[:top_n])
