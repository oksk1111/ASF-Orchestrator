"""소비자용 가격 데이터 라우트.

fresh_alert 앱이 공공 포털 대신 호출하는 정규화 API.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Query

from app.cache import store
from app.core.security import require_consumer
from app.models.schemas import Envelope

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
