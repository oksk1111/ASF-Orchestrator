from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    email: str
    household_size: int = 1
    health_target_keywords: list[str] = Field(default_factory=list)
    monthly_budget: float = 500000.0


class Product(BaseModel):
    product_code: str
    product_name: str
    category_name: str
    origin_location: str
    base_unit: str
    base_price: float
    oversupply_risk_index: float = Field(ge=0.0, le=1.0)
    carbon_emissions_factor: float


class BasketItem(BaseModel):
    product_code: str
    product_name: str
    quantity: int
    unit: str
    original_price: float
    discounted_price: float
    oversupply_risk_level: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    nutrition_match_reason: str
    esg_score_contribution: int


class BasketSummary(BaseModel):
    total_items_count: int
    estimated_original_price: float
    estimated_discounted_price: float
    total_discount_rate: float
    estimated_esg_points: int


class EsgMilestone(BaseModel):
    equivalent_tree_planting_factor: float
    co2_reduction_kg: float


class BasketData(BaseModel):
    user_id: str
    basket_id: str
    calculated_at: datetime
    summary: BasketSummary
    items: list[BasketItem]
    esg_milestone: EsgMilestone


class BasketEnvelope(BaseModel):
    status: Literal["success"] = "success"
    data: BasketData


class ForecastRecord(BaseModel):
    product_code: str
    target_date: str
    p10_predicted_price: float
    p50_predicted_price: float
    p90_predicted_price: float
    oversupply_risk_index: float = Field(ge=0.0, le=1.0)


class ForecastEnvelope(BaseModel):
    status: Literal["success"] = "success"
    data: list[ForecastRecord]


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class DeliveryDestination(BaseModel):
    destination_id: str
    coordinate: Coordinate
    demand_weight_kg: float = Field(gt=0.0)


class CalculateRouteRequest(BaseModel):
    warehouse_id: str
    warehouse_coordinate: Coordinate
    destinations: list[DeliveryDestination]
    vehicle_max_capacity_kg: float = Field(gt=0.0)


class OptimizedRoute(BaseModel):
    route_index: int
    path_destination_ids: list[str]
    total_distance_meters: float
    total_travel_time_seconds: float
    co2_emitted_kg: float


class CalculateRouteResponse(BaseModel):
    warehouse_id: str
    optimized_routes: list[OptimizedRoute]
    base_co2_reduction_percentage: float


class RouteEnvelope(BaseModel):
    status: Literal["success"] = "success"
    data: CalculateRouteResponse


class CheckoutItem(BaseModel):
    product_code: str
    quantity: int = Field(ge=1, default=1)


class CheckoutRequest(BaseModel):
    user_id: str
    basket_items: list[CheckoutItem]
    use_points: bool = True


class CheckoutResponse(BaseModel):
    order_id: str
    user_id: str
    total_amount: float
    discount_amount: float
    points_used: int
    earned_esg_points: int
    wallet_balance: int


class CheckoutEnvelope(BaseModel):
    status: Literal["success"] = "success"
    data: CheckoutResponse


class TokenRequest(BaseModel):
    user_id: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user_id: str
