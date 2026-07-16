"""KAMIS 마스터 데이터 수집기 — 전체 품목 카탈로그 구축.

사용 액션:
- dailySalesList: 전체 품목의 최신 도매/소매가격을 파라미터 없이 일괄 조회.
  품목 목록(universe) 구축에 사용.
- productInfo: 품목/품종/등급 마스터 코드 테이블 조회.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.collectors.base import CollectorError, to_int
from app.models.schemas import PriceRecord

logger = logging.getLogger(__name__)

KAMIS_BASE_URL = "https://www.kamis.or.kr/service/price/xml.do"

# Category codes
CATEGORY_CODES: dict[str, str] = {
    "100": "식량작물",
    "200": "채소류",
    "300": "특용작물",
    "400": "과일류",
    "500": "축산물",
    "600": "수산물",
}


def _parse_price(value: Any) -> int:
    if value in (None, "", "-"):
        return 0
    return to_int(value)


class KamisMasterCollector:
    """KAMIS 전체 품목 카탈로그를 수집한다."""

    def __init__(self, cert_key: str, cert_id: str = "1") -> None:
        self.cert_key = cert_key
        self.cert_id = cert_id or "1"

    async def fetch_catalog(self) -> list[dict[str, Any]]:
        """dailySalesList로 전체 품목의 최신 가격 + 메타정보를 수집한다.

        Returns:
            list of dicts with keys: item_code, item_name, category_code,
            category_name, unit, latest_price, price_direction, price_change_rate,
            product_cls_code, product_cls_name
        """
        if not self.cert_key:
            raise CollectorError("KAMIS 인증키가 설정되지 않았습니다")

        catalog: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            items = await self._request(client, "dailySalesList", {})
            for row in items:
                entry = self._normalize_catalog_entry(row)
                if entry:
                    catalog.append(entry)
        return catalog

    async def fetch_product_info(
        self,
        category_code: str = "",
        item_code: str = "",
        kind_code: str = "",
        rank_code: str = "",
    ) -> list[dict[str, Any]]:
        """productInfo로 품목/품종/등급 마스터 정보를 조회한다."""
        if not self.cert_key:
            raise CollectorError("KAMIS 인증키가 설정되지 않았습니다")

        params: dict[str, str] = {}
        if category_code:
            params["p_itemcategorycode"] = category_code
        if item_code:
            params["p_itemcode"] = item_code
        if kind_code:
            params["p_kindcode"] = kind_code
        if rank_code:
            params["p_productrankcode"] = rank_code

        async with httpx.AsyncClient(timeout=30.0) as client:
            items = await self._request(client, "productInfo", params)
        return items

    async def collect_daily_prices(self) -> list[PriceRecord]:
        """dailySalesList로 가져온 품목에서 PriceRecord를 생성한다.

        dailyPriceByCategoryList와 달리 전체 품목을 한 번에 가져오므로
        카탈로그 빌딩과 동시에 최신 가격도 저장할 수 있다.
        """
        if not self.cert_key:
            raise CollectorError("KAMIS 인증키가 설정되지 않았습니다")

        collected_at = datetime.now(timezone.utc).isoformat()
        records: list[PriceRecord] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            items = await self._request(client, "dailySalesList", {})
            for row in items:
                rec = self._to_price_record(row, collected_at)
                if rec:
                    records.append(rec)
        return records

    async def _request(
        self, client: httpx.AsyncClient, action: str, params: dict[str, str]
    ) -> list[dict]:
        query = {
            "action": action,
            "p_cert_key": self.cert_key,
            "p_cert_id": self.cert_id,
            "p_returntype": "json",
            **params,
        }
        try:
            resp = await client.get(KAMIS_BASE_URL, params=query, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise CollectorError(f"KAMIS 네트워크 오류: {exc}") from exc

        if resp.status_code >= 400:
            raise CollectorError(f"KAMIS HTTP {resp.status_code}: {resp.text[:150]}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise CollectorError(f"KAMIS 비JSON 응답: {resp.text[:150]}") from exc

        # dailySalesList는 최상위에 price/error_code가 있고,
        # productInfo는 data.item 구조를 사용한다.
        # 양쪽 모두 처리한다.
        error_code = str(data.get("error_code", ""))
        if error_code and error_code not in ("000", "001", ""):
            raise CollectorError(f"KAMIS 오류 코드 {error_code}")
        if error_code == "001":
            return []

        # 최상위 price 리스트 (dailySalesList 응답 형식)
        if "price" in data and isinstance(data["price"], list):
            return data["price"]

        # data.item 구조 (productInfo 등 다른 API)
        body = data.get("data")
        if isinstance(body, list):
            code = body[0] if body else "unknown"
            if str(code) == "001":
                return []
            raise CollectorError(f"KAMIS 오류 코드 {code}")

        if not isinstance(body, dict):
            return []
        body_error = str(body.get("error_code", ""))
        if body_error and body_error not in ("000", "001"):
            raise CollectorError(f"KAMIS 오류 코드 {body_error}")

        items = body.get("item") or body.get("price") or []
        if isinstance(items, dict):
            items = [items]
        return items if isinstance(items, list) else []

    def _normalize_catalog_entry(self, row: dict) -> dict[str, Any] | None:
        """dailySalesList 응답 행을 카탈로그 엔트리로 정규화한다."""
        product_name = str(row.get("productName") or row.get("item_name") or "").strip()
        if not product_name:
            return None

        product_no = str(row.get("productno") or row.get("item_code") or "").strip()
        category_code = str(row.get("category_code") or "").strip()
        category_name = str(row.get("category_name") or "").strip()
        unit = str(row.get("unit") or "").strip()
        product_cls_code = str(row.get("product_cls_code") or "").strip()
        product_cls_name = str(row.get("product_cls_name") or "").strip()

        # Latest price (dpr1)
        latest_price = _parse_price(row.get("dpr1"))
        # Direction: 0=down, 1=up, 2=same
        direction_raw = str(row.get("direction") or "2").strip()
        direction_map = {"0": "down", "1": "up", "2": "same"}
        direction = direction_map.get(direction_raw, "same")
        # Change rate
        change_rate = 0.0
        try:
            change_rate = float(str(row.get("value") or "0").replace(",", ""))
        except (ValueError, TypeError):
            pass

        return {
            "item_code": product_no,
            "item_name": product_name,
            "category_code": category_code,
            "category_name": category_name,
            "unit": unit,
            "latest_price": latest_price,
            "price_direction": direction,
            "price_change_rate": change_rate,
            "product_cls_code": product_cls_code,
            "product_cls_name": product_cls_name,
        }

    def _to_price_record(self, row: dict, collected_at: str) -> PriceRecord | None:
        """dailySalesList 응답 행을 PriceRecord로 변환한다."""
        product_name = str(row.get("productName") or row.get("item_name") or "").strip()
        if not product_name:
            return None

        product_no = str(row.get("productno") or row.get("item_code") or "").strip()
        category_code = str(row.get("category_code") or "").strip()
        category_name = str(row.get("category_name") or "").strip()
        unit = str(row.get("unit") or "").strip()
        product_cls_code = str(row.get("product_cls_code") or "01").strip()

        latest_price = _parse_price(row.get("dpr1"))
        day1 = str(row.get("day1") or "").strip()  # "YYYY-MM-DD" or "MM/DD"
        sale_date = day1.replace("-", "").replace("/", "") if day1 else ""
        # If sale_date is short (e.g. "0716"), try to prepend year
        if len(sale_date) == 4:
            sale_date = datetime.now(timezone.utc).strftime("%Y") + sale_date

        cls_name = "소매" if product_cls_code == "01" else "도매"

        return PriceRecord(
            source="KAMIS",
            item_id=f"KAMIS-{category_code}-{product_no}-00-00",
            item_name=product_name,
            category=category_name,
            market_code="",
            market_name=cls_name,
            sale_date=sale_date,
            unit=unit,
            avg_price=latest_price,
            min_price=latest_price,
            max_price=latest_price,
            collected_at=collected_at,
        )
