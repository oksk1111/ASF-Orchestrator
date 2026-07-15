"""품목별 가격 이력(추이) 조회 서비스.

소비자 앱의 상세화면에서 기간별 가격 변화 그래프를 그리고 등락률을 표시하기
위한 시계열 데이터를 만든다.

- KAMIS 품목(item_id가 "KAMIS-"로 시작): kamis.or.kr의 기간별 조회 API를
  실시간으로 호출하여 최대 1년까지의 시계열을 즉시 제공한다 (캐시 적재 기간과
  무관하게 바로 그래프를 그릴 수 있음).
- 그 외 소스(MAFRA 등): 그동안 캐시(price_records)에 쌓아온 일별 기록을 사용한다.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.cache import store
from app.collectors.base import CollectorError
from app.collectors.kamis import KamisCollector
from app.core.config import settings

_MAX_DAYS = 365


def _change_rate(current: int, base: int) -> float | None:
    """base 대비 current의 변화율(%)을 계산한다. base가 없으면 None."""
    if not base:
        return None
    return round((current - base) / base * 100, 2)


async def get_item_history(item_id: str, days: int = 30) -> dict:
    """품목의 기간별 가격 시계열과 등락률을 반환한다."""
    days = max(1, min(days, _MAX_DAYS))

    if item_id.startswith("KAMIS-"):
        series, normal_series, item_name, unit = await _kamis_history(item_id, days)
    else:
        series, item_name, unit = _cached_history(item_id, days)
        normal_series = []

    latest = series[-1]["price"] if series else 0
    previous = series[-2]["price"] if len(series) >= 2 else 0
    first = next((p["price"] for p in series if p["price"] > 0), 0)

    return {
        "item_id": item_id,
        "item_name": item_name,
        "unit": unit,
        "period_days": days,
        "series": series,
        "normal_series": normal_series,
        "current_price": latest,
        "previous_price": previous,
        "change_rate_1d": _change_rate(latest, previous),
        "change_rate_period": _change_rate(latest, first),
    }


async def _kamis_history(
    item_id: str, days: int
) -> tuple[list[dict], list[dict], str, str]:
    parts = item_id.split("-")
    if len(parts) != 5:
        raise CollectorError(f"잘못된 KAMIS item_id 형식: {item_id}")
    _, category_code, item_code, kind_code, rank_code = parts

    now = datetime.now(timezone.utc) + timedelta(hours=9)
    end_day = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    start_day = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    collector = KamisCollector(settings.kamis_cert_key, settings.kamis_cert_id)
    result = await collector.get_period_series(
        item_code, kind_code, rank_code, start_day, end_day, category_code
    )

    # 기간별 API는 품목명/단위를 반환하지 않으므로 캐시에서 보완한다.
    cached = store.query_prices(item_id=item_id, limit=1)
    item_name = cached[0].item_name if cached else item_id
    unit = cached[0].unit if cached else ""

    series = [p for p in result["current"] if p["price"] > 0]
    normal_series = [p for p in result["normal"] if p["price"] > 0]
    return series, normal_series, item_name, unit


def _cached_history(item_id: str, days: int) -> tuple[list[dict], str, str]:
    """캐시에 쌓인 일별 기록에서 시계열을 만든다.

    같은 날짜에 여러 시장 레코드가 있으면 평균값으로 하나의 점을 만든다.
    """
    records = store.query_prices(item_id=item_id, limit=max(days * 20, 200))
    cutoff = (
        datetime.now(timezone.utc) + timedelta(hours=9) - timedelta(days=days)
    ).strftime("%Y%m%d")

    by_date: dict[str, list[int]] = defaultdict(list)
    for r in records:
        if r.sale_date >= cutoff and r.avg_price > 0:
            by_date[r.sale_date].append(r.avg_price)

    series = [
        {"date": d, "price": round(sum(prices) / len(prices))}
        for d, prices in sorted(by_date.items())
    ]
    item_name = records[0].item_name if records else item_id
    unit = records[0].unit if records else ""
    return series, item_name, unit
