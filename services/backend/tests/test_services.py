from app.services.container import recommendation_service
from app.services.pricing import calculate_discount_rate


def test_discount_rate_boundaries() -> None:
    assert calculate_discount_rate(0.0) == 0.05
    assert calculate_discount_rate(1.0) == 0.30
    assert calculate_discount_rate(2.0) == 0.30


def test_recommendation_returns_ranked_items() -> None:
    basket = recommendation_service.build_basket("user_dev_01", k_limit=3)
    assert basket.status == "success"
    assert len(basket.data.items) == 3

    scores = [item.discounted_price for item in basket.data.items]
    assert all(price > 0 for price in scores)
