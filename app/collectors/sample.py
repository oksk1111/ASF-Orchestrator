"""샘플 데이터 생성기.

유효한 API 키가 없어도 서버(소비자 API + 관리자 웹)가 동작하도록
재현 가능한(seed 고정) 정규화 가격 레코드를 생성한다.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.models.schemas import PriceRecord

# (item_id, 품목명, 부류)
_ITEMS: list[tuple[str, str, str]] = [
    ("100-01-003", "상추", "채소류"),
    ("100-01-001", "배추", "채소류"),
    ("100-05-001", "대파", "채소류"),
    ("100-03-001", "무", "채소류"),
    ("100-02-002", "오이", "채소류"),
    ("100-03-002", "감자", "채소류"),
    ("200-01-001", "사과", "과일류"),
    ("200-01-002", "배", "과일류"),
    ("200-02-001", "감귤", "과일류"),
    ("200-04-001", "포도", "과일류"),
    ("300-01-001", "고등어", "수산물"),
    ("300-02-001", "굴", "수산물"),
    ("400-01-001", "한우등심", "축산물"),
    ("400-02-001", "삼겹살", "축산물"),
]

_MARKETS = [("110001", "서울가락"), ("210001", "부산엄궁"), ("340101", "대전오정")]

_BASE_PRICE = {
    "채소류": 3000,
    "과일류": 6000,
    "수산물": 9000,
    "축산물": 18000,
}


def generate_sample_records(days: int = 5, seed: int = 42) -> list[PriceRecord]:
    """최근 `days`일간의 샘플 가격 레코드를 생성한다."""
    rng = random.Random(seed)
    now = datetime.now(timezone.utc) + timedelta(hours=9)  # KST
    collected_at = datetime.now(timezone.utc).isoformat()
    records: list[PriceRecord] = []

    for d in range(days):
        sale_date = (now - timedelta(days=d)).strftime("%Y%m%d")
        for item_id, name, category in _ITEMS:
            base = _BASE_PRICE[category]
            for market_code, market_name in _MARKETS:
                jitter = rng.uniform(0.8, 1.2)
                avg = int(base * jitter)
                spread = int(avg * rng.uniform(0.05, 0.15))
                records.append(
                    PriceRecord(
                        source="SAMPLE",
                        item_id=item_id,
                        item_name=name,
                        category=category,
                        market_code=market_code,
                        market_name=market_name,
                        sale_date=sale_date,
                        unit="1kg",
                        avg_price=avg,
                        min_price=max(0, avg - spread),
                        max_price=avg + spread,
                        collected_at=collected_at,
                    )
                )
    return records
