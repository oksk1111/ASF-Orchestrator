from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _auth_header() -> dict:
    response = client.post("/api/v1/auth/token", json={"user_id": "user_dev_01"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_basket_endpoint() -> None:
    response = client.get("/api/v1/recommendation/basket", headers=_auth_header())
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["summary"]["total_items_count"] > 0
    assert len(payload["data"]["items"]) > 0


def test_forecast_endpoint() -> None:
    response = client.get("/api/v1/forecast/pricing")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert len(payload["data"]) >= 1


def test_ingestion_sync_endpoint() -> None:
    response = client.post("/api/v1/ingestion/sync")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["forecast_records"] >= 1


def test_logistics_endpoint() -> None:
    request_body = {
        "warehouse_id": "WH-SEOUL-01",
        "warehouse_coordinate": {"latitude": 37.5665, "longitude": 126.9780},
        "destinations": [
            {
                "destination_id": "D-1",
                "coordinate": {"latitude": 37.582, "longitude": 127.01},
                "demand_weight_kg": 18.0,
            },
            {
                "destination_id": "D-2",
                "coordinate": {"latitude": 37.55, "longitude": 126.95},
                "demand_weight_kg": 20.0,
            },
        ],
        "vehicle_max_capacity_kg": 25.0,
    }

    response = client.post("/api/v1/logistics/route", json=request_body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert len(payload["data"]["optimized_routes"]) >= 1


def test_checkout_endpoint() -> None:
    headers = _auth_header()
    basket = client.get("/api/v1/recommendation/basket", headers=headers).json()
    first_item = basket["data"]["items"][0]

    request_body = {
        "user_id": "user_dev_01",
        "basket_items": [{"product_code": first_item["product_code"], "quantity": 1}],
        "use_points": True,
    }
    response = client.post("/api/v1/checkout", headers=headers, json=request_body)
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["order_id"]
