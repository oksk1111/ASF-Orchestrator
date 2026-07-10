from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.in_memory import InMemoryRepository
from app.services.forecasting import ForecastingService


class IngestionService:
    def __init__(self, repository: InMemoryRepository, forecasting: ForecastingService) -> None:
        self.repository = repository
        self.forecasting = forecasting

    def sync_public_data(self) -> dict:
        products = self.repository.list_active_products()
        total = len(products)

        forecast_payload = self.forecasting.refresh_forecasts()

        return {
            "status": "success",
            "ingested_sources": ["KAMIS", "RDA", "KMA"],
            "products_seen": total,
            "forecast_records": len(forecast_payload.data),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
