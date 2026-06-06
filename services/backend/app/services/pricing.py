from app.core.config import settings


def calculate_discount_rate(oversupply_risk: float) -> float:
    risk = min(max(oversupply_risk, 0.0), 1.0)
    raw = settings.min_discount_rate + (settings.max_discount_rate - settings.min_discount_rate) * risk
    return round(raw, 2)


def apply_dynamic_pricing(base_price: float, oversupply_risk: float) -> tuple[float, float]:
    discount_rate = calculate_discount_rate(oversupply_risk)
    discounted = round(base_price * (1.0 - discount_rate), 2)
    return discounted, discount_rate


def risk_level(oversupply_risk: float) -> str:
    if oversupply_risk >= 0.85:
        return "VERY_HIGH"
    if oversupply_risk >= 0.65:
        return "HIGH"
    if oversupply_risk >= 0.35:
        return "MEDIUM"
    return "LOW"
