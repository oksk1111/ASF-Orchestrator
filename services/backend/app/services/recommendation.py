from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import settings
from app.domain.models import BasketData, BasketEnvelope, BasketItem, BasketSummary, EsgMilestone, Product
from app.repositories.in_memory import InMemoryRepository
from app.services.feature_store import build_user_features
from app.services.pricing import apply_dynamic_pricing, risk_level


DISTANCE_BY_ORIGIN_KM = {
    "충북 괴산": 72.0,
    "전남 무안": 320.0,
    "경기 이천": 54.0,
    "경북 문경": 190.0,
    "제주": 470.0,
}


def _stable_ratio(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 1000) / 1000.0


def _distance_penalty(origin_location: str) -> float:
    distance = DISTANCE_BY_ORIGIN_KM.get(origin_location, 240.0)
    return min(distance / 500.0, 1.0)


def _nutrition_reason(product: Product, keywords: list[str]) -> str:
    keyword_set = set(keywords)
    if "diabetes" in keyword_set and product.category_name == "vegetable":
        return "사용자 식이섬유 및 저당 식단 조건과 매칭"
    if "high_protein" in keyword_set and product.category_name == "protein":
        return "사용자 단백질 목표 달성 목적과 매칭"
    return "가구 예산 및 선호 카테고리 조합 최적화 결과"


class RecommendationService:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository

    def _utility(self, user_id: str, product_code: str, keyword_signal: float) -> float:
        raw = _stable_ratio(f"{user_id}:{product_code}:utility")
        return round(min(max(raw * 0.7 + keyword_signal * 0.3, 0.0), 1.0), 4)

    def build_basket(self, user_id: str, k_limit: int = 3) -> BasketEnvelope:
        user = self.repository.get_user(user_id)
        if user is None:
            raise ValueError("user not found")

        user_features = build_user_features(user)
        candidates = self.repository.list_active_products()
        scored: list[tuple[float, Product, float]] = []

        for product in candidates:
            utility = self._utility(user.user_id, product.product_code, user_features["keyword_signal"])
            oversupply = product.oversupply_risk_index
            food_mile_penalty = _distance_penalty(product.origin_location)
            total_score = (
                settings.alpha * utility
                + settings.beta * oversupply
                - settings.gamma * food_mile_penalty
            )
            scored.append((total_score, product, food_mile_penalty))

        scored.sort(key=lambda x: x[0], reverse=True)
        picked = scored[:k_limit]

        items: list[BasketItem] = []
        total_original = 0.0
        total_discounted = 0.0
        total_points = 0
        total_co2_reduction = 0.0

        for _, product, food_mile_penalty in picked:
            discounted, _ = apply_dynamic_pricing(product.base_price, product.oversupply_risk_index)
            esg_points = int((product.oversupply_risk_index * 180) + ((1.0 - food_mile_penalty) * 100))
            total_original += product.base_price
            total_discounted += discounted
            total_points += esg_points
            total_co2_reduction += round((1.0 - food_mile_penalty) * product.carbon_emissions_factor, 3)

            items.append(
                BasketItem(
                    product_code=product.product_code,
                    product_name=product.product_name,
                    quantity=1,
                    unit=product.base_unit,
                    original_price=product.base_price,
                    discounted_price=discounted,
                    oversupply_risk_level=risk_level(product.oversupply_risk_index),
                    nutrition_match_reason=_nutrition_reason(product, user.health_target_keywords),
                    esg_score_contribution=esg_points,
                )
            )

        discount_rate = 0.0
        if total_original > 0:
            discount_rate = round((total_original - total_discounted) / total_original, 2)

        summary = BasketSummary(
            total_items_count=len(items),
            estimated_original_price=round(total_original, 2),
            estimated_discounted_price=round(total_discounted, 2),
            total_discount_rate=discount_rate,
            estimated_esg_points=total_points,
        )
        milestone = EsgMilestone(
            equivalent_tree_planting_factor=round(total_co2_reduction / 20.0, 2),
            co2_reduction_kg=round(total_co2_reduction, 2),
        )
        data = BasketData(
            user_id=user.user_id,
            basket_id=str(uuid4()),
            calculated_at=datetime.now(timezone.utc),
            summary=summary,
            items=items,
            esg_milestone=milestone,
        )
        return BasketEnvelope(data=data)
