"""KAMIS 가격 추세 조회기 — 실시간 API 호출로 추세 데이터를 반환.

사용 액션:
- recentlyPriceTrendList: 최근 40일 가격 추세 (10일 간격)
- monthlyPriceTrendList: 월별 평균 가격 추세
- yearlyPriceTrendList: 연도별 평균 가격 추세
- monthlySalesList: 월별 상세 가격 (최대 3년, m1~m12)
- yearlySalesList: 연도별 통계 (평균/최대/최소/표준편차)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.collectors.base import CollectorError, to_int

logger = logging.getLogger(__name__)

KAMIS_BASE_URL = "https://www.kamis.or.kr/service/price/xml.do"


def _parse_price(value: Any) -> int:
    if value in (None, "", "-"):
        return 0
    return to_int(value)


class KamisTrendCollector:
    """KAMIS 가격 추세 데이터를 실시간 API 호출로 조회한다."""

    def __init__(self, cert_key: str, cert_id: str = "1") -> None:
        self.cert_key = cert_key
        self.cert_id = cert_id or "1"

    async def get_recent_trend(self, product_no: str, reg_day: str = "") -> dict[str, Any]:
        """최근 40일 가격 추세를 조회한다 (10일 간격 5개 가격점).

        Args:
            product_no: 품목 코드 (e.g., "212" for 배추)
            reg_day: 기준일 (YYYY-MM-DD). 없으면 최신 조사일.

        Returns:
            {"product_no": str, "prices": [{"days_ago": int, "price": int}, ...],
             "max_price": int, "min_price": int}
        """
        params: dict[str, str] = {"p_productno": product_no}
        if reg_day:
            params["p_regday"] = reg_day

        items = await self._request("recentlyPriceTrendList", params)
        prices: list[dict[str, Any]] = []
        max_price = 0
        min_price = 0

        for row in items:
            for key, days_ago in [("d0", 0), ("d10", 10), ("d20", 20), ("d30", 30), ("d40", 40)]:
                p = _parse_price(row.get(key))
                if p > 0:
                    prices.append({"days_ago": days_ago, "price": p})
            max_price = _parse_price(row.get("mx"))
            min_price = _parse_price(row.get("mn"))

        return {
            "product_no": product_no,
            "prices": prices,
            "max_price": max_price,
            "min_price": min_price,
        }

    async def get_monthly_trend(self, product_no: str, reg_day: str = "") -> list[dict[str, Any]]:
        """월별 평균 가격 추세를 조회한다.

        Returns:
            [{"yyyymm": "202601", "max_price": int, "min_price": int}, ...]
        """
        params: dict[str, str] = {"p_productno": product_no}
        if reg_day:
            params["p_regday"] = reg_day

        items = await self._request("monthlyPriceTrendList", params)
        result: list[dict[str, Any]] = []
        for row in items:
            yyyymm = str(row.get("yyyymm") or "").strip()
            if yyyymm:
                result.append({
                    "yyyymm": yyyymm,
                    "max_price": _parse_price(row.get("max")),
                    "min_price": _parse_price(row.get("min")),
                })
        return result

    async def get_yearly_trend(self, product_no: str, reg_day: str = "") -> list[dict[str, Any]]:
        """연도별 평균 가격 추세를 조회한다.

        Returns:
            [{"yyyy": "2025", "max_price": int, "min_price": int}, ...]
        """
        params: dict[str, str] = {"p_productno": product_no}
        if reg_day:
            params["p_regday"] = reg_day

        items = await self._request("yearlyPriceTrendList", params)
        result: list[dict[str, Any]] = []
        for row in items:
            yyyy = str(row.get("yyyy") or "").strip()
            if yyyy:
                result.append({
                    "yyyy": yyyy,
                    "max_price": _parse_price(row.get("max")),
                    "min_price": _parse_price(row.get("min")),
                })
        return result

    async def get_monthly_sales(
        self,
        item_code: str,
        kind_code: str = "",
        category_code: str = "",
        year: str = "",
        period: str = "3",
        county_code: str = "",
    ) -> list[dict[str, Any]]:
        """월별 상세 가격을 조회한다 (최대 3년, m1~m12 + yearavg).

        Returns:
            [{"yyyy": str, "product_cls": str, "months": [int x 12], "year_avg": int}, ...]
        """
        now = datetime.now(timezone.utc) + timedelta(hours=9)
        params: dict[str, str] = {
            "p_yyyy": year or str(now.year),
            "p_period": period,
            "p_itemcode": item_code,
        }
        if kind_code:
            params["p_kindcode"] = kind_code
        if category_code:
            params["p_itemcategorycode"] = category_code
        if county_code:
            params["p_countycode"] = county_code

        items = await self._request("monthlySalesList", params)
        result: list[dict[str, Any]] = []
        for row in items:
            yyyy = str(row.get("yyyy") or "").strip()
            if not yyyy:
                continue
            months = [_parse_price(row.get(f"m{i}")) for i in range(1, 13)]
            result.append({
                "yyyy": yyyy,
                "product_cls": str(row.get("productclscode") or "").strip(),
                "months": months,
                "year_avg": _parse_price(row.get("yearavg")),
            })
        return result

    async def get_yearly_sales(
        self,
        item_code: str,
        kind_code: str = "",
        category_code: str = "",
        year: str = "",
        county_code: str = "",
    ) -> list[dict[str, Any]]:
        """연도별 통계를 조회한다 (평균/최대/최소/표준편차/변동계수).

        Returns:
            [{"year": str, "avg": int, "max": int, "min": int, "stddev": float, "cv": float}, ...]
        """
        now = datetime.now(timezone.utc) + timedelta(hours=9)
        params: dict[str, str] = {
            "p_yyyy": year or str(now.year),
            "p_itemcode": item_code,
        }
        if kind_code:
            params["p_kindcode"] = kind_code
        if category_code:
            params["p_itemcategorycode"] = category_code
        if county_code:
            params["p_countycode"] = county_code

        items = await self._request("yearlySalesList", params)
        result: list[dict[str, Any]] = []
        for row in items:
            div = str(row.get("div") or "").strip()
            if not div:
                continue
            result.append({
                "year": div,
                "avg": _parse_price(row.get("avg_data")),
                "max": _parse_price(row.get("max_data")),
                "min": _parse_price(row.get("min_data")),
                "stddev": float(str(row.get("stddev_data") or "0").replace(",", "") or "0"),
                "cv": float(str(row.get("cv_data") or "0").replace(",", "") or "0"),
            })
        return result

    async def _request(self, action: str, params: dict[str, str]) -> list[dict]:
        query = {
            "action": action,
            "p_cert_key": self.cert_key,
            "p_cert_id": self.cert_id,
            "p_returntype": "json",
            **params,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
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

        # 응답 구조 처리: 일부 API는 최상위에 price/error_code가 있고
        # 다른 API는 data.item 구조를 사용한다.
        error_code = str(data.get("error_code", ""))
        if error_code and error_code not in ("000", "001", ""):
            raise CollectorError(f"KAMIS 오류 코드 {error_code}")
        if error_code == "001":
            return []

        # 최상위 price 리스트 (dailySalesList, recentlyPriceTrendList 등)
        if "price" in data and isinstance(data["price"], list):
            return data["price"]

        # data.item 구조
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
