"""FreshAlert price analysis engine.

Provides functions for calculating price drop rates, quantity changes,
seasonal scoring, anomaly detection, and recommendation scoring for
agricultural product price alerts.
"""

from __future__ import annotations

import statistics

# Recommendation score weights
WEIGHT_QTY_INCREASE = 0.3
WEIGHT_PRICE_DROP = 0.4
WEIGHT_SEASON_BONUS = 0.3

# Thresholds
SIGNIFICANT_DROP_ZSCORE = -2.0
CRITICAL_DROP_ZSCORE = -3.0
DEFAULT_PRICE_DROP_THRESHOLD = -15.0  # percent


def calculate_moving_average(prices: list[int], window: int = 30) -> float:
    """Calculate simple moving average over the given window."""
    if not prices:
        return 0.0
    subset = prices[-window:]
    return sum(subset) / len(subset)


def calculate_price_drop_rate(current_price: int, avg_30d: float) -> float:
    """Calculate price drop rate as percentage.

    Returns negative value when price dropped (e.g., -22.5 means 22.5% cheaper).
    """
    if avg_30d <= 0:
        return 0.0
    return round((current_price - avg_30d) / avg_30d * 100, 2)


def calculate_qty_increase_rate(current_qty: int, avg_7d_qty: float) -> float:
    """Calculate quantity increase rate as percentage."""
    if avg_7d_qty <= 0:
        return 0.0
    return round((current_qty - avg_7d_qty) / avg_7d_qty * 100, 2)


def is_in_season(month: int, season_start: int | None, season_end: int | None) -> bool:
    """Check if current month is in the item's season."""
    if season_start is None or season_end is None:
        return False
    if season_start <= season_end:
        return season_start <= month <= season_end
    # Wraps around year (e.g., Nov-Feb: start=11, end=2)
    return month >= season_start or month <= season_end


def normalize(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Normalize a value to 0-1 range."""
    if max_val <= min_val:
        return 0.0
    clamped = max(min_val, min(value, max_val))
    return (clamped - min_val) / (max_val - min_val)


def calculate_recommend_score(
    price_drop_rate: float,
    qty_increase_rate: float,
    is_season: bool,
) -> float:
    """Calculate recommendation score (0.0 ~ 1.0).

    Score = (qty_increase_normalized * 0.3) + (price_drop_normalized * 0.4) + (season_bonus * 0.3)
    """
    # Normalize: price_drop_rate is negative when favorable (-50 to 0 maps to 1.0 to 0.0)
    price_score = normalize(abs(price_drop_rate), 0.0, 50.0)
    qty_score = normalize(qty_increase_rate, 0.0, 100.0)
    season_bonus = 1.0 if is_season else 0.0

    score = (
        qty_score * WEIGHT_QTY_INCREASE
        + price_score * WEIGHT_PRICE_DROP
        + season_bonus * WEIGHT_SEASON_BONUS
    )
    return round(min(1.0, max(0.0, score)), 3)


def detect_price_anomaly(current_price: int, price_history: list[int]) -> str:
    """Detect price anomaly using Z-score.

    Returns:
        "CRITICAL_DROP" - Z-score < -3 (extreme price drop)
        "SIGNIFICANT_DROP" - Z-score < -2 (notable price drop)
        "NORMAL" - within normal range
    """
    if len(price_history) < 7:
        return "NORMAL"

    mean = statistics.mean(price_history)
    stdev = statistics.stdev(price_history)

    if stdev == 0:
        return "NORMAL"

    z_score = (current_price - mean) / stdev

    if z_score < CRITICAL_DROP_ZSCORE:
        return "CRITICAL_DROP"
    elif z_score < SIGNIFICANT_DROP_ZSCORE:
        return "SIGNIFICANT_DROP"
    return "NORMAL"


def check_keyword_trigger(
    current_price: int,
    avg_30d: float,
    threshold_type: str,
    threshold_value: float,
) -> bool:
    """Check if a keyword subscription should trigger an alert.

    Args:
        current_price: today's price
        avg_30d: 30-day moving average
        threshold_type: "percentage" or "absolute"
        threshold_value: -15 (for 15% drop) or 12000 (absolute price in won)

    Returns:
        True if alert should be triggered
    """
    if threshold_type == "percentage":
        drop_rate = calculate_price_drop_rate(current_price, avg_30d)
        return drop_rate <= threshold_value  # threshold is negative, e.g. -15
    elif threshold_type == "absolute":
        return current_price <= threshold_value
    return False


def select_top_recommendations(
    analyses: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """Select top N items by recommendation score.

    Args:
        analyses: list of dicts with at least 'recommend_score', 'price_drop_rate'
                  and items must have price_drop_rate < 0 (actually cheaper)
        top_n: number of items to return

    Returns:
        Top N items sorted by recommend_score descending
    """
    # Only include items that are actually cheaper than average
    eligible = [a for a in analyses if a.get("price_drop_rate", 0) < 0]
    sorted_items = sorted(eligible, key=lambda x: x["recommend_score"], reverse=True)
    return sorted_items[:top_n]
