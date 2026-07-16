"""KAMIS 지역별 가격 조회기.

사용 액션:
- dailyCountyList: 지역별 최신 도소매 가격 비교
- ItemInfo: 특정 품목의 지역별 상세 가격 (현재/1주/1달/1년)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.collectors.base import CollectorError, to_int

logger = logging.getLogger(__name__)

KAMIS_BASE_URL = "https://www.kamis.or.kr/service/price/xml.do"

# 소매 지역코드
RETAIL_COUNTY_CODES: dict[str, str] = {
    "1101": "서울", "2100": "부산", "2200": "대구", "2300": "인천",
    "2401": "광주", "2501": "대전", "2601": "울산", "2701": "세종",
    "3111": "수원", "3112": "성남", "3113": "의정부", "3138": "고양",
    "3145": "용인", "3211": "춘천", "3214": "강릉", "3311": "청주",
    "3411": "천안", "3511": "전주", "3613": "순천", "3711": "포항",
    "3714": "안동", "3814": "창원", "3818": "김해", "3911": "제주",
}

# 도매 지역코드
WHOLESALE_COUNTY_CODES: dict[str, str] = {
    "1101": "서울", "2100": "부산", "2200": "대구",
    "2401": "광주", "2501": "대전",
}


def _parse_price(value: Any) -> int:
    if value in (None, "", "-"):
        return 0
    return to_int(value)


class KamisRegionalCollector:
    """KAMIS 지역별 가격 데이터를 조회한다."""

    def __init__(self, cert_key: str, cert_id: str = "1") -> None:
        self.cert_key = cert_key
        self.cert_id = cert_id or "1"

    async def get_daily_county(self, county_code: str) -> list[dict[str, Any]]:
        """특정 지역의 최신 도소매 가격을 조회한다.

        Args:
            county_code: 지역 코드 (e.g., "1101" for 서울)

        Returns:
            [{"product_name": str, "county_code": str, "day1": str, "price1": int,
              "day2": str, "price2": int, ..., "direction": str, "change_rate": float}, ...]
        """
        if not self.cert_key:
            raise CollectorError("KAMIS 인증키가 설정되지 않았습니다")

        items = await self._request("dailyCountyList", {"p_countycode": county_code})
        result: list[dict[str, Any]] = []
        for row in items:
            product_name = str(row.get("productName") or "").strip()
            if not product_name:
                continue
            direction_raw = str(row.get("direction") or "2").strip()
            direction_map = {"0": "down", "1": "up", "2": "same"}
            change_rate = 0.0
            try:
                change_rate = float(str(row.get("value") or "0").replace(",", ""))
            except (ValueError, TypeError):
                pass

            result.append({
                "product_name": product_name,
                "county_code": county_code,
                "county_name": RETAIL_COUNTY_CODES.get(county_code, county_code),
                "day1": str(row.get("day1") or "").strip(),
                "price1": _parse_price(row.get("dpr1")),
                "day2": str(row.get("day2") or "").strip(),
                "price2": _parse_price(row.get("dpr2")),
                "day3": str(row.get("day3") or "").strip(),
                "price3": _parse_price(row.get("dpr3")),
                "day4": str(row.get("day4") or "").strip(),
                "price4": _parse_price(row.get("dpr4")),
                "direction": direction_map.get(direction_raw, "same"),
                "change_rate": change_rate,
            })
        return result

    async def get_item_regional(
        self,
        item_code: str,
        kind_code: str = "",
        rank_code: str = "",
        category_code: str = "",
        product_cls_code: str = "01",
        reg_day: str = "",
    ) -> list[dict[str, Any]]:
        """특정 품목의 지역별 가격을 조회한다 (ItemInfo 액션).

        Returns:
            [{"county_name": str, "unit": str, "price": int,
              "week_price": int, "month_price": int, "year_price": int}, ...]
        """
        if not self.cert_key:
            raise CollectorError("KAMIS 인증키가 설정되지 않았습니다")

        params: dict[str, str] = {
            "p_productclscode": product_cls_code,
            "p_itemcode": item_code,
        }
        if kind_code:
            params["p_kindcode"] = kind_code
        if rank_code:
            params["p_productrankcode"] = rank_code
        if category_code:
            params["p_itemcategorycode"] = category_code
        if reg_day:
            params["p_regday"] = reg_day

        items = await self._request("ItemInfo", params)
        result: list[dict[str, Any]] = []
        for row in items:
            county_name = str(row.get("countyname") or "").strip()
            if not county_name:
                continue
            result.append({
                "county_name": county_name,
                "unit": str(row.get("unit") or "").strip(),
                "price": _parse_price(row.get("price")),
                "week_price": _parse_price(row.get("weekprice")),
                "month_price": _parse_price(row.get("monthprice")),
                "year_price": _parse_price(row.get("yearprice")),
            })
        return result

    async def get_all_regions_prices(self, county_codes: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """주요 지역의 전체 품목 가격을 일괄 조회한다.

        주의: 지역 수 × API 호출이므로 주요 5개 도시만 기본으로 호출.
        """
        if not self.cert_key:
            raise CollectorError("KAMIS 인증키가 설정되지 않았습니다")

        codes = county_codes or WHOLESALE_COUNTY_CODES
        all_results: list[dict[str, Any]] = []
        for code, name in codes.items():
            try:
                region_data = await self.get_daily_county(code)
                all_results.extend(region_data)
            except CollectorError as e:
                logger.warning("지역 %s(%s) 조회 실패: %s", name, code, e)
        return all_results

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

        # 응답 구조: 최상위 price 리스트 또는 data.item 구조
        error_code = str(data.get("error_code") or data.get("result_code") or "")
        if error_code and error_code not in ("000", "0", "001", ""):
            raise CollectorError(f"KAMIS 오류 코드 {error_code}")
        if error_code == "001":
            return []

        if "price" in data and isinstance(data["price"], list):
            return data["price"]

        body = data.get("data")
        if isinstance(body, list):
            code = body[0] if body else "unknown"
            if str(code) == "001":
                return []
            raise CollectorError(f"KAMIS 오류 코드 {code}")

        if not isinstance(body, dict):
            return []
        body_error = str(body.get("error_code") or body.get("result_code") or "")
        if body_error and body_error not in ("000", "0", "001"):
            raise CollectorError(f"KAMIS 오류 코드 {body_error}")

        items = body.get("item") or body.get("price") or []
        if isinstance(items, dict):
            items = [items]
        return items if isinstance(items, list) else []
