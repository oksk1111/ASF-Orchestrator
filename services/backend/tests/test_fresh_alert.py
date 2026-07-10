"""FreshAlert 서비스 테스트."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.fresh_alert.analyzer import (
    calculate_moving_average,
    calculate_price_drop_rate,
    calculate_qty_increase_rate,
    calculate_recommend_score,
    check_keyword_trigger,
    detect_price_anomaly,
    is_in_season,
    normalize,
    select_top_recommendations,
)
from app.services.fresh_alert.repository import fresh_alert_repo


client = TestClient(app)


# ─── Analyzer Unit Tests ────────────────────────────────────────────────────


class TestMovingAverage:
    def test_basic(self):
        prices = [100, 200, 300, 400, 500]
        assert calculate_moving_average(prices, 5) == 300.0

    def test_window_larger_than_data(self):
        prices = [100, 200, 300]
        assert calculate_moving_average(prices, 30) == 200.0

    def test_empty(self):
        assert calculate_moving_average([], 30) == 0.0

    def test_window_subset(self):
        prices = list(range(1, 101))  # 1~100
        # Last 10: 91~100, avg = 95.5
        assert calculate_moving_average(prices, 10) == 95.5


class TestPriceDropRate:
    def test_drop(self):
        # 10000 -> 8000: -20%
        result = calculate_price_drop_rate(8000, 10000.0)
        assert result == -20.0

    def test_increase(self):
        # 10000 -> 12000: +20%
        result = calculate_price_drop_rate(12000, 10000.0)
        assert result == 20.0

    def test_zero_avg(self):
        assert calculate_price_drop_rate(5000, 0.0) == 0.0

    def test_same_price(self):
        assert calculate_price_drop_rate(10000, 10000.0) == 0.0


class TestQtyIncreaseRate:
    def test_increase(self):
        result = calculate_qty_increase_rate(150, 100.0)
        assert result == 50.0

    def test_decrease(self):
        result = calculate_qty_increase_rate(50, 100.0)
        assert result == -50.0

    def test_zero_avg(self):
        assert calculate_qty_increase_rate(100, 0.0) == 0.0


class TestIsInSeason:
    def test_in_season_normal(self):
        assert is_in_season(7, 6, 8) is True

    def test_out_of_season(self):
        assert is_in_season(3, 6, 8) is False

    def test_wrap_around(self):
        # Nov-Feb season
        assert is_in_season(12, 11, 2) is True
        assert is_in_season(1, 11, 2) is True
        assert is_in_season(5, 11, 2) is False

    def test_none_season(self):
        assert is_in_season(7, None, None) is False


class TestRecommendScore:
    def test_perfect_score(self):
        score = calculate_recommend_score(
            price_drop_rate=-50.0,  # max drop
            qty_increase_rate=100.0,  # max increase
            is_season=True,
        )
        assert score == 1.0

    def test_zero_score(self):
        score = calculate_recommend_score(
            price_drop_rate=0.0,
            qty_increase_rate=0.0,
            is_season=False,
        )
        assert score == 0.0

    def test_season_bonus(self):
        score_no_season = calculate_recommend_score(-20.0, 30.0, False)
        score_season = calculate_recommend_score(-20.0, 30.0, True)
        assert score_season > score_no_season


class TestDetectAnomaly:
    def test_normal(self):
        prices = [10000] * 30
        assert detect_price_anomaly(10000, prices) == "NORMAL"

    def test_significant_drop(self):
        prices = [10000] * 30
        # Mean=10000, std=0 -> can't detect with zero std
        # Use varied prices
        prices = [10000 + i * 100 for i in range(30)]
        mean = sum(prices) / len(prices)
        import statistics
        std = statistics.stdev(prices)
        extreme_low = int(mean - 2.5 * std)
        assert detect_price_anomaly(extreme_low, prices) == "SIGNIFICANT_DROP"

    def test_insufficient_data(self):
        assert detect_price_anomaly(5000, [10000, 9000]) == "NORMAL"


class TestKeywordTrigger:
    def test_percentage_triggered(self):
        assert check_keyword_trigger(8000, 10000.0, "percentage", -15.0) is True

    def test_percentage_not_triggered(self):
        assert check_keyword_trigger(9000, 10000.0, "percentage", -15.0) is False

    def test_absolute_triggered(self):
        assert check_keyword_trigger(11000, 15000.0, "absolute", 12000.0) is True

    def test_absolute_not_triggered(self):
        assert check_keyword_trigger(15000, 15000.0, "absolute", 12000.0) is False


class TestSelectTopRecommendations:
    def test_basic(self):
        analyses = [
            {"item_id": "a", "recommend_score": 0.9, "price_drop_rate": -30},
            {"item_id": "b", "recommend_score": 0.7, "price_drop_rate": -20},
            {"item_id": "c", "recommend_score": 0.5, "price_drop_rate": -10},
            {"item_id": "d", "recommend_score": 0.3, "price_drop_rate": 5},  # not cheaper
        ]
        result = select_top_recommendations(analyses, top_n=2)
        assert len(result) == 2
        assert result[0]["item_id"] == "a"
        assert result[1]["item_id"] == "b"

    def test_excludes_positive_drop(self):
        analyses = [
            {"item_id": "a", "recommend_score": 0.9, "price_drop_rate": 10},  # more expensive
        ]
        result = select_top_recommendations(analyses, top_n=5)
        assert len(result) == 0


# ─── Repository Tests ────────────────────────────────────────────────────────


class TestRepository:
    def test_list_items(self):
        items = fresh_alert_repo.list_items()
        assert len(items) > 0

    def test_get_item(self):
        items = fresh_alert_repo.list_items()
        item = fresh_alert_repo.get_item(items[0].item_id)
        assert item is not None
        assert item.item_id == items[0].item_id

    def test_search_items(self):
        results = fresh_alert_repo.search_items("배추")
        assert len(results) > 0
        assert any(
            "배추" in r.mid_name or "배추" in r.large_name or "배추" in r.small_name
            for r in results
        )

    def test_get_price_history(self):
        items = fresh_alert_repo.list_items()
        history = fresh_alert_repo.get_price_history(items[0].item_id, days=30)
        assert len(history) > 0

    def test_keyword_subscription_crud(self):
        from app.domain.fresh_alert_models import KeywordSubscription

        user_id = "test_user"
        sub = KeywordSubscription(
            id="test_sub_1",
            user_id=user_id,
            item_id="100-01-001",
            item_name="배추",
            threshold_type="percentage",
            threshold_value=-15.0,
            enabled=True,
        )
        fresh_alert_repo.add_keyword_subscription(user_id, sub)

        subs = fresh_alert_repo.get_keyword_subscriptions(user_id)
        assert len(subs) >= 1
        assert any(s.id == "test_sub_1" for s in subs)

        # Update
        updated = fresh_alert_repo.update_keyword_subscription(
            user_id, "test_sub_1", {"threshold_value": -20.0}
        )
        assert updated is not None
        assert updated.threshold_value == -20.0

        # Delete
        assert fresh_alert_repo.delete_keyword_subscription(user_id, "test_sub_1") is True
        assert fresh_alert_repo.delete_keyword_subscription(user_id, "nonexistent") is False


# ─── API Integration Tests ───────────────────────────────────────────────────


class TestFreshAlertAPI:
    def test_get_recommendations(self):
        resp = client.get("/api/v1/fresh-alert/recommendations/today")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "items" in data["data"]

    def test_search_items(self):
        resp = client.get("/api/v1/fresh-alert/items/search", params={"q": "사과"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_get_categories(self):
        resp = client.get("/api/v1/fresh-alert/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["data"]) > 0

    def test_get_current_season(self):
        resp = client.get("/api/v1/fresh-alert/seasons/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "month" in data["data"]
        assert "vegetables" in data["data"]
        assert "fruits" in data["data"]

    def test_get_season_calendar(self):
        resp = client.get("/api/v1/fresh-alert/seasons/calendar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 12

    def test_keyword_crud_flow(self):
        # Create
        resp = client.post(
            "/api/v1/fresh-alert/keywords",
            params={"user_id": "api_test_user"},
            json={
                "item_id": "100-01-001",
                "item_name": "배추",
                "threshold_type": "percentage",
                "threshold_value": -15.0,
            },
        )
        assert resp.status_code == 201
        keyword_id = resp.json()["data"]["id"]

        # Read
        resp = client.get(
            "/api/v1/fresh-alert/keywords",
            params={"user_id": "api_test_user"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

        # Update
        resp = client.put(
            f"/api/v1/fresh-alert/keywords/{keyword_id}",
            params={"user_id": "api_test_user"},
            json={"threshold_value": -20.0},
        )
        assert resp.status_code == 200

        # Delete
        resp = client.delete(
            f"/api/v1/fresh-alert/keywords/{keyword_id}",
            params={"user_id": "api_test_user"},
        )
        assert resp.status_code == 200

    def test_category_subscribe_flow(self):
        # Subscribe
        resp = client.post(
            "/api/v1/fresh-alert/categories/subscribe",
            params={"user_id": "api_test_user"},
            json={
                "large_code": "100",
                "large_name": "채소류",
                "mid_code": "01",
                "mid_name": "엽경채류",
            },
        )
        assert resp.status_code == 201
        sub_id = resp.json()["data"]["id"]

        # Read subscribed
        resp = client.get(
            "/api/v1/fresh-alert/categories/subscribed",
            params={"user_id": "api_test_user"},
        )
        assert resp.status_code == 200

        # Unsubscribe
        resp = client.delete(
            f"/api/v1/fresh-alert/categories/subscribe/{sub_id}",
            params={"user_id": "api_test_user"},
        )
        assert resp.status_code == 200

    def test_notifications(self):
        resp = client.get(
            "/api/v1/fresh-alert/notifications",
            params={"user_id": "user_dev_01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_item_not_found(self):
        resp = client.get("/api/v1/fresh-alert/items/NONEXISTENT")
        assert resp.status_code == 404
