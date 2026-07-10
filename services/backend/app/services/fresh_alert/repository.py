"""FreshAlert in-memory repository.

Pre-populated with Korean seasonal produce items and mock price data.
Will be backed by PostgreSQL in a future iteration.
"""

from __future__ import annotations

import random
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.fresh_alert_models import (
    CategorySubscription,
    DailyAnalysis,
    DailyRecommendation,
    Item,
    KeywordSubscription,
    Notification,
    PriceRecord,
)

# ---------------------------------------------------------------------------
# Season calendar: month -> vegetables, fruits, seafood (Korean seasonal produce)
# ---------------------------------------------------------------------------

SEASON_CALENDAR: dict[int, dict[str, list[str]]] = {
    1: {
        "vegetables": ["시금치", "무", "배추"],
        "fruits": ["귤", "딸기"],
        "seafood": ["꼬막", "대구"],
    },
    2: {
        "vegetables": ["냉이", "달래", "봄동"],
        "fruits": ["딸기", "한라봉"],
        "seafood": ["꼬막", "도미"],
    },
    3: {
        "vegetables": ["냉이", "쑥", "미나리"],
        "fruits": ["딸기"],
        "seafood": ["조개", "주꾸미"],
    },
    4: {
        "vegetables": ["두릅", "취나물", "부추"],
        "fruits": ["딸기", "참외"],
        "seafood": ["멍게", "키조개"],
    },
    5: {
        "vegetables": ["양배추", "감자", "양파"],
        "fruits": ["참외", "앵두"],
        "seafood": ["장어", "전복"],
    },
    6: {
        "vegetables": ["오이", "상추", "깻잎"],
        "fruits": ["수박", "자두", "매실"],
        "seafood": ["전복", "성게"],
    },
    7: {
        "vegetables": ["옥수수", "토마토", "호박"],
        "fruits": ["수박", "복숭아", "포도"],
        "seafood": ["전복", "민어"],
    },
    8: {
        "vegetables": ["고추", "가지", "옥수수"],
        "fruits": ["포도", "복숭아", "자두"],
        "seafood": ["전복", "광어"],
    },
    9: {
        "vegetables": ["고구마", "토란"],
        "fruits": ["사과", "배", "포도"],
        "seafood": ["꽃게", "대하"],
    },
    10: {
        "vegetables": ["무", "배추", "고구마"],
        "fruits": ["사과", "배", "감"],
        "seafood": ["꽃게", "대하", "전어"],
    },
    11: {
        "vegetables": ["무", "배추", "시금치"],
        "fruits": ["감", "귤", "유자"],
        "seafood": ["굴", "과메기"],
    },
    12: {
        "vegetables": ["시금치", "무"],
        "fruits": ["귤", "딸기"],
        "seafood": ["굴", "방어", "과메기"],
    },
}

# ---------------------------------------------------------------------------
# Pre-populated items (Korean produce)
# ---------------------------------------------------------------------------

ITEMS: list[Item] = [
    # 채소류(100) - 엽경채류(01)
    Item(
        item_id="100-01-001",
        large_code="100",
        mid_code="01",
        small_code="001",
        large_name="채소류",
        mid_name="엽경채류",
        small_name="배추",
        season_start=10,
        season_end=2,
    ),
    Item(
        item_id="100-01-002",
        large_code="100",
        mid_code="01",
        small_code="002",
        large_name="채소류",
        mid_name="엽경채류",
        small_name="시금치",
        season_start=11,
        season_end=3,
    ),
    Item(
        item_id="100-01-003",
        large_code="100",
        mid_code="01",
        small_code="003",
        large_name="채소류",
        mid_name="엽경채류",
        small_name="상추",
        season_start=4,
        season_end=6,
    ),
    Item(
        item_id="100-01-004",
        large_code="100",
        mid_code="01",
        small_code="004",
        large_name="채소류",
        mid_name="엽경채류",
        small_name="깻잎",
        season_start=6,
        season_end=9,
    ),
    Item(
        item_id="100-01-005",
        large_code="100",
        mid_code="01",
        small_code="005",
        large_name="채소류",
        mid_name="엽경채류",
        small_name="양배추",
        season_start=4,
        season_end=6,
    ),
    # 채소류(100) - 과채류(02)
    Item(
        item_id="100-02-001",
        large_code="100",
        mid_code="02",
        small_code="001",
        large_name="채소류",
        mid_name="과채류",
        small_name="토마토",
        season_start=6,
        season_end=9,
    ),
    Item(
        item_id="100-02-002",
        large_code="100",
        mid_code="02",
        small_code="002",
        large_name="채소류",
        mid_name="과채류",
        small_name="오이",
        season_start=5,
        season_end=8,
    ),
    Item(
        item_id="100-02-003",
        large_code="100",
        mid_code="02",
        small_code="003",
        large_name="채소류",
        mid_name="과채류",
        small_name="고추",
        season_start=7,
        season_end=9,
    ),
    Item(
        item_id="100-02-004",
        large_code="100",
        mid_code="02",
        small_code="004",
        large_name="채소류",
        mid_name="과채류",
        small_name="호박",
        season_start=6,
        season_end=9,
    ),
    # 채소류(100) - 근채류(03)
    Item(
        item_id="100-03-001",
        large_code="100",
        mid_code="03",
        small_code="001",
        large_name="채소류",
        mid_name="근채류",
        small_name="무",
        season_start=10,
        season_end=2,
    ),
    Item(
        item_id="100-03-002",
        large_code="100",
        mid_code="03",
        small_code="002",
        large_name="채소류",
        mid_name="근채류",
        small_name="감자",
        season_start=5,
        season_end=7,
    ),
    Item(
        item_id="100-03-003",
        large_code="100",
        mid_code="03",
        small_code="003",
        large_name="채소류",
        mid_name="근채류",
        small_name="고구마",
        season_start=9,
        season_end=11,
    ),
    # 과일류(200) - 인과류(01)
    Item(
        item_id="200-01-001",
        large_code="200",
        mid_code="01",
        small_code="001",
        large_name="과일류",
        mid_name="인과류",
        small_name="사과",
        season_start=9,
        season_end=11,
    ),
    Item(
        item_id="200-01-002",
        large_code="200",
        mid_code="01",
        small_code="002",
        large_name="과일류",
        mid_name="인과류",
        small_name="배",
        season_start=9,
        season_end=11,
    ),
    # 과일류(200) - 감귤류(02)
    Item(
        item_id="200-02-001",
        large_code="200",
        mid_code="02",
        small_code="001",
        large_name="과일류",
        mid_name="감귤류",
        small_name="귤",
        season_start=11,
        season_end=2,
    ),
    # 과일류(200) - 핵과류(03)
    Item(
        item_id="200-03-001",
        large_code="200",
        mid_code="03",
        small_code="001",
        large_name="과일류",
        mid_name="핵과류",
        small_name="복숭아",
        season_start=7,
        season_end=9,
    ),
    # 과일류(200) - 장과류(04)
    Item(
        item_id="200-04-001",
        large_code="200",
        mid_code="04",
        small_code="001",
        large_name="과일류",
        mid_name="장과류",
        small_name="포도",
        season_start=8,
        season_end=10,
    ),
    Item(
        item_id="200-04-002",
        large_code="200",
        mid_code="04",
        small_code="002",
        large_name="과일류",
        mid_name="장과류",
        small_name="딸기",
        season_start=12,
        season_end=4,
    ),
    Item(
        item_id="200-04-003",
        large_code="200",
        mid_code="04",
        small_code="003",
        large_name="과일류",
        mid_name="장과류",
        small_name="수박",
        season_start=6,
        season_end=8,
    ),
    # 수산물(300) - 어류(01)
    Item(
        item_id="300-01-001",
        large_code="300",
        mid_code="01",
        small_code="001",
        large_name="수산물",
        mid_name="어류",
        small_name="고등어",
        season_start=9,
        season_end=12,
    ),
    Item(
        item_id="300-01-002",
        large_code="300",
        mid_code="01",
        small_code="002",
        large_name="수산물",
        mid_name="어류",
        small_name="방어",
        season_start=11,
        season_end=2,
    ),
    Item(
        item_id="300-01-003",
        large_code="300",
        mid_code="01",
        small_code="003",
        large_name="수산물",
        mid_name="어류",
        small_name="광어",
        season_start=6,
        season_end=8,
    ),
    # 수산물(300) - 패류(02)
    Item(
        item_id="300-02-001",
        large_code="300",
        mid_code="02",
        small_code="001",
        large_name="수산물",
        mid_name="패류",
        small_name="굴",
        season_start=11,
        season_end=2,
    ),
    Item(
        item_id="300-02-002",
        large_code="300",
        mid_code="02",
        small_code="002",
        large_name="수산물",
        mid_name="패류",
        small_name="전복",
        season_start=5,
        season_end=8,
    ),
    # 수산물(300) - 갑각류(03)
    Item(
        item_id="300-03-001",
        large_code="300",
        mid_code="03",
        small_code="001",
        large_name="수산물",
        mid_name="갑각류",
        small_name="꽃게",
        season_start=9,
        season_end=11,
    ),
    # 축산물(400) - 소(01)
    Item(
        item_id="400-01-001",
        large_code="400",
        mid_code="01",
        small_code="001",
        large_name="축산물",
        mid_name="소",
        small_name="한우등심",
        season_start=None,
        season_end=None,
    ),
    # 축산물(400) - 돼지(02)
    Item(
        item_id="400-02-001",
        large_code="400",
        mid_code="02",
        small_code="001",
        large_name="축산물",
        mid_name="돼지",
        small_name="삼겹살",
        season_start=None,
        season_end=None,
    ),
    # 축산물(400) - 닭/오리(03)
    Item(
        item_id="400-03-001",
        large_code="400",
        mid_code="03",
        small_code="001",
        large_name="축산물",
        mid_name="닭/오리",
        small_name="닭",
        season_start=None,
        season_end=None,
    ),
]

# ---------------------------------------------------------------------------
# Price ranges per item (원/kg or unit-appropriate prices)
# ---------------------------------------------------------------------------

_PRICE_RANGES: dict[str, tuple[int, int]] = {
    "100-01-001": (2000, 4000),   # 배추
    "100-01-002": (4000, 8000),   # 시금치
    "100-01-003": (3000, 6000),   # 상추
    "100-01-004": (3000, 5000),   # 깻잎
    "100-01-005": (1500, 3000),   # 양배추
    "100-02-001": (3000, 6000),   # 토마토
    "100-02-002": (2000, 4000),   # 오이
    "100-02-003": (5000, 10000),  # 고추
    "100-02-004": (2000, 4000),   # 호박
    "100-03-001": (800, 1500),    # 무
    "100-03-002": (2000, 3500),   # 감자
    "100-03-003": (2000, 4000),   # 고구마
    "200-01-001": (5000, 9000),   # 사과
    "200-01-002": (4000, 8000),   # 배
    "200-02-001": (3000, 6000),   # 귤
    "200-03-001": (5000, 10000),  # 복숭아
    "200-04-001": (6000, 12000),  # 포도
    "200-04-002": (10000, 20000), # 딸기
    "200-04-003": (1500, 3000),   # 수박
    "300-01-001": (5000, 8000),   # 고등어
    "300-01-002": (8000, 15000),  # 방어
    "300-01-003": (10000, 18000), # 광어
    "300-02-001": (8000, 15000),  # 굴
    "300-02-002": (20000, 40000), # 전복
    "300-03-001": (15000, 30000), # 꽃게
    "400-01-001": (50000, 90000), # 한우등심
    "400-02-001": (15000, 25000), # 삼겹살
    "400-03-001": (4000, 7000),   # 닭
}


def _is_in_season(month: int, season_start: int | None, season_end: int | None) -> bool:
    """Check if a given month falls within the item's season range."""
    if season_start is None or season_end is None:
        return True  # Year-round (축산물 etc.)
    if season_start <= season_end:
        return season_start <= month <= season_end
    # Wraps around year boundary (e.g., start=11, end=2)
    return month >= season_start or month <= season_end


def _generate_mock_prices(rng: random.Random) -> dict[str, list[PriceRecord]]:
    """Generate 30 days of mock price data for each item.

    Prices follow seasonal trends: cheaper in season, more expensive out.
    """
    today = datetime.now(timezone.utc).date()
    price_history: dict[str, list[PriceRecord]] = {}

    for item in ITEMS:
        item_id = item.item_id
        price_range = _PRICE_RANGES.get(item_id)
        if price_range is None:
            continue

        low, high = price_range
        mid_price = (low + high) // 2
        spread = (high - low) // 2

        records: list[PriceRecord] = []
        for day_offset in range(30, 0, -1):
            record_date = today - timedelta(days=day_offset)
            month = record_date.month

            # Seasonal adjustment: in-season items are 20-40% cheaper
            in_season = _is_in_season(month, item.season_start, item.season_end)
            if in_season:
                seasonal_factor = rng.uniform(0.6, 0.85)
            else:
                seasonal_factor = rng.uniform(1.0, 1.3)

            # Base price with seasonal factor
            base = int(mid_price * seasonal_factor)

            # Daily fluctuation (+/- 10%)
            daily_noise = rng.uniform(-0.10, 0.10)
            avg_price = int(base * (1 + daily_noise))

            # Clamp within reasonable bounds
            avg_price = max(low // 2, min(avg_price, high * 2))

            # Min/max spread around average
            min_price = int(avg_price * rng.uniform(0.85, 0.95))
            max_price = int(avg_price * rng.uniform(1.05, 1.15))

            # Quantity and amount (realistic daily volumes for a wholesale market)
            total_qty = rng.randint(500, 5000)
            total_amt = avg_price * total_qty

            record = PriceRecord(
                item_id=item_id,
                market_code="110001",
                market_name="서울가락",
                sale_date=record_date.isoformat(),
                avg_price=avg_price,
                min_price=min_price,
                max_price=max_price,
                total_qty=total_qty,
                total_amt=total_amt,
                data_source="KAMIS",
            )
            records.append(record)

        price_history[item_id] = records

    return price_history


# ---------------------------------------------------------------------------
# Repository class
# ---------------------------------------------------------------------------


class FreshAlertRepository:
    """In-memory FreshAlert data store.

    Pre-populated with mock items and price history for development.
    """

    def __init__(self) -> None:
        self.items: dict[str, Item] = {item.item_id: item for item in ITEMS}

        # Generate reproducible mock price data
        rng = random.Random(42)
        self.price_history: dict[str, list[PriceRecord]] = _generate_mock_prices(rng)

        self.keyword_subscriptions: dict[str, list[KeywordSubscription]] = {}
        self.category_subscriptions: dict[str, list[CategorySubscription]] = {}
        self.notifications: dict[str, list[Notification]] = {}
        self.daily_analyses: list[DailyAnalysis] = []
        self.recommendations: list[DailyRecommendation] = []

    # --- Item queries ---

    def get_item(self, item_id: str) -> Item | None:
        return self.items.get(item_id)

    def list_items(self) -> list[Item]:
        return list(self.items.values())

    def search_items(self, query: str) -> list[Item]:
        """Search items by name (large_name, mid_name, small_name)."""
        query_lower = query.lower()
        results: list[Item] = []
        for item in self.items.values():
            if (
                query_lower in item.large_name.lower()
                or query_lower in item.mid_name.lower()
                or query_lower in item.small_name.lower()
            ):
                results.append(item)
        return results

    def get_items_by_category(
        self, large_code: str, mid_code: str | None = None
    ) -> list[Item]:
        results: list[Item] = []
        for item in self.items.values():
            if item.large_code != large_code:
                continue
            if mid_code is not None and item.mid_code != mid_code:
                continue
            results.append(item)
        return results

    # --- Price records ---

    def add_price_record(self, record: PriceRecord) -> None:
        if record.item_id not in self.price_history:
            self.price_history[record.item_id] = []
        self.price_history[record.item_id].append(record)

    def get_price_history(self, item_id: str, days: int = 30) -> list[PriceRecord]:
        records = self.price_history.get(item_id, [])
        if days >= len(records):
            return deepcopy(records)
        return deepcopy(records[-days:])

    def get_latest_price(self, item_id: str) -> PriceRecord | None:
        records = self.price_history.get(item_id, [])
        if not records:
            return None
        return deepcopy(records[-1])

    # --- Keyword subscriptions ---

    def add_keyword_subscription(
        self, user_id: str, sub: KeywordSubscription
    ) -> KeywordSubscription:
        if user_id not in self.keyword_subscriptions:
            self.keyword_subscriptions[user_id] = []
        self.keyword_subscriptions[user_id].append(sub)
        return sub

    def get_keyword_subscriptions(self, user_id: str) -> list[KeywordSubscription]:
        return deepcopy(self.keyword_subscriptions.get(user_id, []))

    def delete_keyword_subscription(self, user_id: str, sub_id: str) -> bool:
        subs = self.keyword_subscriptions.get(user_id, [])
        for i, s in enumerate(subs):
            if s.id == sub_id:
                subs.pop(i)
                return True
        return False

    def update_keyword_subscription(
        self, user_id: str, sub_id: str, updates: dict
    ) -> KeywordSubscription | None:
        subs = self.keyword_subscriptions.get(user_id, [])
        for i, s in enumerate(subs):
            if s.id == sub_id:
                updated = s.model_copy(update=updates)
                subs[i] = updated
                return updated
        return None

    # --- Category subscriptions ---

    def add_category_subscription(
        self, user_id: str, sub: CategorySubscription
    ) -> CategorySubscription:
        if user_id not in self.category_subscriptions:
            self.category_subscriptions[user_id] = []
        self.category_subscriptions[user_id].append(sub)
        return sub

    def get_category_subscriptions(self, user_id: str) -> list[CategorySubscription]:
        return deepcopy(self.category_subscriptions.get(user_id, []))

    def delete_category_subscription(self, user_id: str, sub_id: str) -> bool:
        subs = self.category_subscriptions.get(user_id, [])
        for i, s in enumerate(subs):
            if s.id == sub_id:
                subs.pop(i)
                return True
        return False

    # --- Daily analyses ---

    def save_daily_analysis(self, item_id: str, analysis: DailyAnalysis) -> None:
        self.daily_analyses.append(analysis)

    def get_daily_analyses(self, date: str | None = None) -> list[DailyAnalysis]:
        if date is None:
            return deepcopy(self.daily_analyses)
        return deepcopy(
            [a for a in self.daily_analyses if a.analysis_date == date]
        )

    # --- Recommendations ---

    def save_recommendation(self, rec: DailyRecommendation) -> None:
        self.recommendations.append(rec)

    def get_latest_recommendation(self) -> DailyRecommendation | None:
        if not self.recommendations:
            return None
        return deepcopy(self.recommendations[-1])

    # --- Notifications ---

    def add_notification(self, notif: Notification) -> None:
        if notif.user_id not in self.notifications:
            self.notifications[notif.user_id] = []
        self.notifications[notif.user_id].append(notif)

    def get_notifications(self, user_id: str, limit: int = 50) -> list[Notification]:
        notifs = self.notifications.get(user_id, [])
        # Return most recent first
        return deepcopy(notifs[-limit:][::-1])

    def mark_notification_read(self, user_id: str, notif_id: str) -> bool:
        notifs = self.notifications.get(user_id, [])
        for notif in notifs:
            if notif.id == notif_id:
                notif.read_at = datetime.now(timezone.utc).isoformat()
                return True
        return False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

fresh_alert_repo = FreshAlertRepository()
