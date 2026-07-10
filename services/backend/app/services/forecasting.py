from __future__ import annotations

from datetime import date, timedelta

from app.domain.models import ForecastEnvelope, ForecastRecord, Product
from app.repositories.in_memory import InMemoryRepository
from app.services.feature_store import build_product_features


class ForecastingService:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository

    def refresh_forecasts(self) -> ForecastEnvelope:
        products = self.repository.list_active_products()
        today = date.today()
        records: list[dict] = []

        for product in products:
            features = build_product_features(product)
            drift = 1.0 + (features["price_volatility"] - 0.2) * 0.08
            risk_adjustment = 1.0 - (product.oversupply_risk_index * 0.12)
            p50 = round(product.base_price * drift * risk_adjustment, 2)
            p10 = round(p50 * 0.88, 2)
            p90 = round(p50 * 1.16, 2)

            records.append(
                {
                    "product_code": product.product_code,
                    "target_date": (today + timedelta(days=14)).isoformat(),
                    "p10_predicted_price": p10,
                    "p50_predicted_price": p50,
                    "p90_predicted_price": p90,
                    "oversupply_risk_index": product.oversupply_risk_index,
                }
            )

        self.repository.save_forecasts(records)
        return ForecastEnvelope(data=[ForecastRecord(**record) for record in records])

    def list_forecasts(self) -> ForecastEnvelope:
        records = self.repository.list_forecasts()
        if not records:
            return self.refresh_forecasts()
        return ForecastEnvelope(data=[ForecastRecord(**record) for record in records])
