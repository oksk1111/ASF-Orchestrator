from __future__ import annotations

from app.repositories.in_memory import repo
from app.services.checkout import CheckoutService
from app.services.forecasting import ForecastingService
from app.services.ingestion import IngestionService
from app.services.logistics import LogisticsService
from app.services.recommendation import RecommendationService

forecasting_service = ForecastingService(repo)
recommendation_service = RecommendationService(repo)
logistics_service = LogisticsService()
checkout_service = CheckoutService(repo)
ingestion_service = IngestionService(repo, forecasting_service)
