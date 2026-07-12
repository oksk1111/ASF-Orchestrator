"""ASF-Orchestrator 중간 서버 API 테스트."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cache import store
from app.core.config import settings
from app.main import app
from app.services import ingest


@pytest.fixture(scope="module")
def client() -> TestClient:
    # 임시 캐시 DB로 격리
    tmp = Path(tempfile.gettempdir()) / "asf_orch_test_cache.db"
    if tmp.exists():
        tmp.unlink()
    settings.cache_db_path = str(tmp)
    store.init_db()
    ingest.run_sample_sync()  # 샘플 적재
    return TestClient(app)


def _basic(user: str, pw: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


class TestHealth:
    def test_healthz(self, client: TestClient):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["cache_records"] > 0


class TestConsumerApi:
    def test_prices(self, client: TestClient):
        resp = client.get("/api/v1/prices?limit=10")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list) and len(data) > 0
        assert {"source", "item_id", "avg_price"} <= set(data[0].keys())

    def test_items(self, client: TestClient):
        resp = client.get("/api/v1/items")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) > 0

    def test_sources(self, client: TestClient):
        resp = client.get("/api/v1/sources")
        assert resp.status_code == 200
        sources = [s["source"] for s in resp.json()["data"]]
        assert "SAMPLE" in sources

    def test_recommendations(self, client: TestClient):
        resp = client.get("/api/v1/recommendations/today?top_n=5")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) <= 5
        if data:
            assert "price_drop_rate" in data[0]


class TestAdmin:
    def test_admin_requires_auth(self, client: TestClient):
        resp = client.get("/admin")
        assert resp.status_code == 401

    def test_admin_dashboard(self, client: TestClient):
        resp = client.get("/admin", headers=_basic(settings.admin_username, settings.admin_password))
        assert resp.status_code == 200
        assert "대시보드" in resp.text or "Admin" in resp.text

    def test_admin_collect_sample(self, client: TestClient):
        resp = client.post(
            "/admin/collect",
            data={"source": "SAMPLE"},
            headers=_basic(settings.admin_username, settings.admin_password),
            follow_redirects=False,
        )
        assert resp.status_code == 303
