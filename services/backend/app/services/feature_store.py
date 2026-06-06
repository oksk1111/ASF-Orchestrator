import hashlib

from app.domain.models import Product, UserProfile


def _stable_ratio(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 1000) / 1000.0


def build_product_features(product: Product) -> dict:
    return {
        "price_volatility": 0.1 + (_stable_ratio(product.product_code) * 0.4),
        "seasonal_strength": 0.3 + (_stable_ratio(product.product_code + ":season") * 0.7),
        "transport_risk": 0.1 + (_stable_ratio(product.origin_location) * 0.5),
    }


def build_user_features(user: UserProfile) -> dict:
    keyword_signal = 0.2 + (_stable_ratio(user.user_id + ":keyword") * 0.8)
    budget_signal = min(max(user.monthly_budget / 500000.0, 0.2), 1.2)
    return {
        "keyword_signal": keyword_signal,
        "budget_signal": budget_signal,
        "household_signal": min(max(user.household_size / 4.0, 0.25), 1.0),
    }
