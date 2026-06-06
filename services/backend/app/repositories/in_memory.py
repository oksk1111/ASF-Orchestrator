from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.models import Product, UserProfile


class InMemoryRepository:
    def __init__(self) -> None:
        self._users: dict[str, UserProfile] = {
            "user_dev_01": UserProfile(
                user_id="user_dev_01",
                email="user1@asf.local",
                household_size=3,
                health_target_keywords=["diabetes", "high_fiber"],
                monthly_budget=450000,
            ),
            "user_dev_02": UserProfile(
                user_id="user_dev_02",
                email="user2@asf.local",
                household_size=1,
                health_target_keywords=["high_protein"],
                monthly_budget=300000,
            ),
        }
        self._products: dict[str, Product] = {
            "AGRI-CABB-001": Product(
                product_code="AGRI-CABB-001",
                product_name="유기농 괴산 양배추",
                category_name="vegetable",
                origin_location="충북 괴산",
                base_unit="개",
                base_price=3000.0,
                oversupply_risk_index=0.85,
                carbon_emissions_factor=1.4,
            ),
            "AGRI-ONIO-053": Product(
                product_code="AGRI-ONIO-053",
                product_name="햇 양파",
                category_name="vegetable",
                origin_location="전남 무안",
                base_unit="망",
                base_price=4500.0,
                oversupply_risk_index=0.95,
                carbon_emissions_factor=1.8,
            ),
            "AGRI-CARR-201": Product(
                product_code="AGRI-CARR-201",
                product_name="제주 흙당근",
                category_name="vegetable",
                origin_location="제주",
                base_unit="봉",
                base_price=3800.0,
                oversupply_risk_index=0.62,
                carbon_emissions_factor=1.6,
            ),
            "AGRI-TOFU-901": Product(
                product_code="AGRI-TOFU-901",
                product_name="국산 두부",
                category_name="protein",
                origin_location="경기 이천",
                base_unit="팩",
                base_price=2200.0,
                oversupply_risk_index=0.44,
                carbon_emissions_factor=0.6,
            ),
            "AGRI-APPL-110": Product(
                product_code="AGRI-APPL-110",
                product_name="문경 사과",
                category_name="fruit",
                origin_location="경북 문경",
                base_unit="봉",
                base_price=6200.0,
                oversupply_risk_index=0.52,
                carbon_emissions_factor=2.1,
            ),
        }
        self._forecast_records: list[dict] = []
        self._wallets: dict[str, int] = {
            "user_dev_01": 500,
            "user_dev_02": 200,
        }
        self._orders: list[dict] = []

    def get_default_user_id(self) -> str:
        return next(iter(self._users.keys()))

    def get_user(self, user_id: str) -> UserProfile | None:
        return self._users.get(user_id)

    def list_active_products(self) -> list[Product]:
        return list(self._products.values())

    def get_product(self, product_code: str) -> Product | None:
        return self._products.get(product_code)

    def save_forecasts(self, records: list[dict]) -> None:
        self._forecast_records = deepcopy(records)

    def list_forecasts(self) -> list[dict]:
        return deepcopy(self._forecast_records)

    def get_wallet_points(self, user_id: str) -> int:
        return self._wallets.get(user_id, 0)

    def set_wallet_points(self, user_id: str, value: int) -> None:
        self._wallets[user_id] = max(0, value)

    def append_order(self, payload: dict) -> dict:
        order = {
            "order_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        self._orders.append(order)
        return deepcopy(order)

    def list_orders(self) -> list[dict]:
        return deepcopy(self._orders)


repo = InMemoryRepository()
