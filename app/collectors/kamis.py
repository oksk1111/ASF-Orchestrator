"""KAMIS(한국농수산식품유통공사) 일별 도·소매 가격 수집기 — data.go.kr 버전.

엔드포인트: https://apis.data.go.kr/B552845/perDay/price
데이터셋: https://www.data.go.kr/data/15156057/openapi.do (serviceKey 방식)

주의: data.go.kr 응답의 정확한 JSON 필드명은 API 명세서에 따라 다를 수 있다.
유효한 serviceKey로 첫 수집 시 원본 키를 로그로 남기고, 필요하면 매핑을 확정한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.collectors.base import CollectorError, to_int
from app.models.schemas import PriceRecord

logger = logging.getLogger(__name__)

KAMIS_BASE_URL = "https://apis.data.go.kr/B552845/perDay/price"

# 구분코드(도매/소매) — 응답에 존재할 경우 이름 매핑에 사용
CLS_NAMES = {"1": "소매", "01": "소매", "2": "도매", "02": "도매"}


def _first(row: dict[str, Any], keys: list[str], default: str = "") -> str:
    """여러 후보 키 중 처음으로 존재하는 값을 문자열로 반환한다."""
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return str(row[k]).strip()
    return default


class KamisCollector:
    """KAMIS(data.go.kr) 일별 가격 수집기."""

    def __init__(self, service_key: str) -> None:
        self.service_key = service_key

    async def collect(self, num_rows: int = 300, max_pages: int = 3) -> list[PriceRecord]:
        """일별 가격을 수집한다.

        Raises:
            CollectorError: 인증/네트워크/파싱 오류.
        """
        if not self.service_key:
            raise CollectorError("KAMIS serviceKey가 설정되지 않았습니다")

        records: list[PriceRecord] = []
        collected_at = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in range(1, max_pages + 1):
                rows = await self._fetch(client, page, num_rows)
                if not rows:
                    break
                if page == 1 and rows:
                    logger.info("KAMIS 원본 필드 키: %s", list(rows[0].keys()))
                for row in rows:
                    rec = self._normalize(row, collected_at)
                    if rec is not None:
                        records.append(rec)
                if len(rows) < num_rows:
                    break
        return records

    async def _fetch(self, client: httpx.AsyncClient, page: int, num_rows: int) -> list[dict]:
        params = {
            "serviceKey": self.service_key,
            "pageNo": str(page),
            "numOfRows": str(num_rows),
            "type": "json",
        }
        try:
            resp = await client.get(KAMIS_BASE_URL, params=params)
        except httpx.HTTPError as exc:
            raise CollectorError(f"KAMIS 네트워크 오류: {exc}") from exc

        if resp.status_code == 401:
            raise CollectorError("KAMIS 401 Unauthorized — serviceKey 미등록/무효")
        if resp.status_code >= 400:
            raise CollectorError(f"KAMIS HTTP {resp.status_code}: {resp.text[:150]}")

        try:
            data = resp.json()
        except ValueError as exc:
            # XML 에러 응답 등
            raise CollectorError(f"KAMIS 비JSON 응답: {resp.text[:150]}") from exc

        return self._extract_rows(data)

    def _extract_rows(self, data: Any) -> list[dict]:
        """data.go.kr 표준 응답 구조에서 item 리스트를 추출한다."""
        if not isinstance(data, dict):
            return []
        response = data.get("response", data)
        header = response.get("header", {}) if isinstance(response, dict) else {}
        result_code = str(header.get("resultCode", "")).strip()
        if result_code and result_code not in ("00", "0", "000"):
            raise CollectorError(
                f"KAMIS 오류 코드 {result_code}: {header.get('resultMsg', '')}"
            )

        body = response.get("body", {}) if isinstance(response, dict) else {}
        items = body.get("items", body) if isinstance(body, dict) else body
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):  # 단일 item
            items = [items]
        return items if isinstance(items, list) else []

    def _normalize(self, row: dict, collected_at: str) -> PriceRecord | None:
        # 정확한 키는 명세서에 따라 조정 (아래는 관대한 후보 매핑)
        item_name = _first(row, ["itemName", "품목명", "pumName", "itemNm", "prdlstNm"])
        if not item_name:
            return None
        item_code = _first(row, ["itemCode", "품목코드", "itemCd", "prdlstCode"], item_name)
        cls_code = _first(row, ["clsCode", "구분코드", "prdlstClsCode"])
        price = to_int(
            _first(row, ["price", "조사일가격", "examinPrice", "delngPrice", "surveyPrice"])
        )
        return PriceRecord(
            source="KAMIS",
            item_id=f"KAMIS-{item_code}",
            item_name=item_name,
            category=_first(row, ["categoryName", "부류명", "clsName", "prdlstClsNm"]),
            market_code=_first(row, ["marketCode", "시장코드", "delngGrpCode"]),
            market_name=_first(
                row, ["marketName", "시장명", "delngGrpNm"], CLS_NAMES.get(cls_code, "소매")
            ),
            sale_date=_first(
                row, ["surveyDate", "조사일자", "examinDate", "delngDate"]
            ).replace("-", ""),
            unit=_first(row, ["unit", "단위", "unitNm"]),
            avg_price=price,
            min_price=price,
            max_price=price,
            collected_at=collected_at,
        )
