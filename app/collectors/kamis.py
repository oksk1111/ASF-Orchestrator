"""KAMIS(한국농수산식품유통공사) 가격정보 수집기 — kamis.or.kr 원본 Open API.

주의: data.go.kr에 래핑된 버전(B552845/perDay)이 아니라 KAMIS가 직접 운영하는
kamis.or.kr/service/price/xml.do 엔드포인트를 사용한다 (2026-07-16 실제 데이터
확인됨. data.go.kr 버전은 데이터가 비어있어 사용 중단함).

사용 액션:
- dailyPriceByCategoryList: 부류(카테고리)별 당일/전일/1주일전/1개월전/1년전/평년
  가격을 한 번에 반환 → 일별 시세 목록 수집에 사용.
- periodProductList: 특정 품목/품종/등급의 기간별 일별 가격 시계열 반환
  (최대 1년) → 품목 상세 화면의 가격 추이 그래프에 사용 (app/services/history.py).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.collectors.base import CollectorError, to_int
from app.models.schemas import PriceRecord

logger = logging.getLogger(__name__)

KAMIS_BASE_URL = "https://www.kamis.or.kr/service/price/xml.do"

# 부류코드(대분류) → 이름
CATEGORY_CODES: dict[str, str] = {
    "100": "식량작물",
    "200": "채소류",
    "300": "특용작물",
    "400": "과일류",
    "500": "축산물",
    "600": "수산물",
}

# 구분코드 → 이름 (도매/소매)
CLS_NAMES = {"01": "도매", "02": "소매"}


def _kst_yesterday() -> str:
    """KST 기준 어제 날짜(YYYY-MM-DD). 당일 데이터는 보통 아직 미발행 상태(0원)이다."""
    now = datetime.now(timezone.utc) + timedelta(hours=9)
    return (now - timedelta(days=1)).strftime("%Y-%m-%d")


def _parse_price(value: Any) -> int:
    """"12,345" / "-" 형태의 가격 문자열을 int로 변환한다."""
    if value in (None, "", "-"):
        return 0
    return to_int(value)


class KamisCollector:
    """KAMIS(kamis.or.kr) 일별 가격 + 기간별 가격추이 수집기."""

    def __init__(self, cert_key: str, cert_id: str = "1") -> None:
        self.cert_key = cert_key
        self.cert_id = cert_id or "1"

    async def collect(self, reg_day: str | None = None) -> list[PriceRecord]:
        """지정일(없으면 어제)의 부류별 도매/소매가격을 전체 수집한다.

        Raises:
            CollectorError: 인증/네트워크/파싱 오류.
        """
        if not self.cert_key:
            raise CollectorError("KAMIS 인증키(KAMIS_CERT_KEY)가 설정되지 않았습니다")

        day = reg_day or _kst_yesterday()
        collected_at = datetime.now(timezone.utc).isoformat()
        records: list[PriceRecord] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for category_code, category_name in CATEGORY_CODES.items():
                for cls_code, cls_name in CLS_NAMES.items():
                    items = await self._request(
                        client,
                        "dailyPriceByCategoryList",
                        {
                            "p_product_cls_code": cls_code,
                            "p_item_category_code": category_code,
                            "p_regday": day,
                            "p_convert_kg_yn": "N",
                        },
                    )
                    for row in items:
                        rec = self._normalize_daily(
                            row, category_code, category_name, cls_name, day, collected_at
                        )
                        if rec is not None:
                            records.append(rec)
        return records

    async def get_period_series(
        self,
        item_code: str,
        kind_code: str,
        rank_code: str,
        start_day: str,
        end_day: str,
        category_code: str = "",
    ) -> dict[str, list[dict[str, Any]]]:
        """특정 품목/품종/등급의 기간별 일별 가격(평균/평년)을 조회한다.

        Returns:
            {"current": [{"date": "YYYYMMDD", "price": int}, ...],
             "normal": [{"date": "YYYYMMDD", "price": int}, ...]}
        """
        if not self.cert_key:
            raise CollectorError("KAMIS 인증키(KAMIS_CERT_KEY)가 설정되지 않았습니다")

        async with httpx.AsyncClient(timeout=30.0) as client:
            rows = await self._request(
                client,
                "periodProductList",
                {
                    "p_startday": start_day,
                    "p_endday": end_day,
                    "p_itemcategorycode": category_code,
                    "p_itemcode": item_code,
                    "p_kindcode": kind_code,
                    "p_productrankcode": rank_code,
                    "p_convert_kg_yn": "N",
                },
            )

        current: list[dict[str, Any]] = []
        normal: list[dict[str, Any]] = []
        for row in rows:
            county = str(row.get("countyname") or "").strip()
            yyyy = str(row.get("yyyy") or "").strip()
            regday = str(row.get("regday") or "").strip()  # "MM/DD"
            price = _parse_price(row.get("price"))
            if not yyyy or not regday or "/" not in regday:
                continue
            mm, _, dd = regday.partition("/")
            date = f"{yyyy}{mm.zfill(2)}{dd.zfill(2)}"
            point = {"date": date, "price": price}
            # p_countycode를 지정하지 않으면 지역별 개별 행이 함께 내려오므로
            # 전국 집계 행("평균"/"평년")만 사용한다 (그 외 지역 행은 무시).
            if county == "평년":
                normal.append(point)
            elif county == "평균":
                current.append(point)

        current.sort(key=lambda p: p["date"])
        normal.sort(key=lambda p: p["date"])
        return {"current": current, "normal": normal}

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

        body = data.get("data")
        if isinstance(body, list):
            # 오류 응답: {"data": ["900"]} 형태 (필수 파라미터 누락/인증 오류 등)
            code = body[0] if body else "unknown"
            raise CollectorError(f"KAMIS 오류 코드 {code}")

        if not isinstance(body, dict):
            return []
        error_code = str(body.get("error_code", ""))
        if error_code and error_code != "000":
            raise CollectorError(f"KAMIS 오류 코드 {error_code}")

        items = body.get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items if isinstance(items, list) else []

    def _normalize_daily(
        self,
        row: dict,
        category_code: str,
        category_name: str,
        cls_name: str,
        day: str,
        collected_at: str,
    ) -> PriceRecord | None:
        item_name = str(row.get("item_name") or "").strip()
        if not item_name:
            return None
        item_code = str(row.get("item_code") or "").strip()
        kind_name = str(row.get("kind_name") or "").strip()
        kind_code = str(row.get("kind_code") or "").strip()
        rank_name = str(row.get("rank") or "").strip()
        rank_code = str(row.get("rank_code") or "").strip()

        full_name = item_name
        if kind_name:
            full_name = f"{item_name}({kind_name})"

        price = _parse_price(row.get("dpr1"))
        return PriceRecord(
            source="KAMIS",
            item_id=f"KAMIS-{category_code}-{item_code}-{kind_code}-{rank_code}",
            item_name=full_name,
            category=category_name,
            market_code="",
            market_name=f"{cls_name}({rank_name})" if rank_name else cls_name,
            sale_date=day.replace("-", ""),
            unit=str(row.get("unit") or "").strip(),
            avg_price=price,
            min_price=price,
            max_price=price,
            collected_at=collected_at,
        )

