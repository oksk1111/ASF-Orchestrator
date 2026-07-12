"""MAFRA(농림축산식품부 도매시장 통합) OpenAPI 수집기.

엔드포인트: http://211.237.50.150:7080/openapi/{apiKey}/json/{gridId}/{start}/{end}
정산가격(SETTLEMENT_PRICE) 그리드를 수집하여 정규화된 PriceRecord로 변환한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.collectors.base import CollectorError, to_int
from app.models.schemas import PriceRecord

logger = logging.getLogger(__name__)

MAFRA_BASE_URL = "http://211.237.50.150:7080/openapi"
SETTLEMENT_PRICE = "Grid_20240625000000000653_1"

# 주요 도매시장 코드 → 이름
MARKET_CODES: dict[str, str] = {
    "110001": "서울가락",
    "110008": "서울강서",
    "210001": "부산엄궁",
    "310101": "대구북부",
    "320301": "인천삼산",
    "340101": "대전오정",
}


def _kst_yesterday() -> str:
    """정산은 보통 전일 기준 → KST 어제 날짜(YYYYMMDD)."""
    now = datetime.now(timezone.utc) + timedelta(hours=9)
    return (now - timedelta(days=1)).strftime("%Y%m%d")


class MafraCollector:
    """MAFRA 정산가격 수집기."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def collect(self, sale_date: str | None = None) -> list[PriceRecord]:
        """지정일(없으면 어제)의 정산가격을 수집한다.

        Raises:
            CollectorError: 인증/네트워크/파싱 오류.
        """
        date = sale_date or _kst_yesterday()
        records: list[PriceRecord] = []
        collected_at = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for market_code, market_name in MARKET_CODES.items():
                rows = await self._fetch(client, date, market_code)
                for row in rows:
                    rec = self._normalize(row, market_code, market_name, date, collected_at)
                    if rec is not None:
                        records.append(rec)
        return records

    async def _fetch(
        self, client: httpx.AsyncClient, sale_date: str, market_code: str
    ) -> list[dict]:
        url = f"{MAFRA_BASE_URL}/{self.api_key}/json/{SETTLEMENT_PRICE}/1/300"
        params = {"SALEDATE": sale_date, "WHSALCD": market_code}
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise CollectorError(f"MAFRA HTTP 오류: {exc}") from exc
        except ValueError as exc:
            raise CollectorError(f"MAFRA 응답 파싱 오류: {exc}") from exc

        # 인증 오류 확인
        result = data.get("result")
        if isinstance(result, dict) and result.get("code", "").startswith("INFO"):
            raise CollectorError(f"MAFRA 인증 오류: {result.get('message', result.get('code'))}")

        grid = data.get(SETTLEMENT_PRICE)
        if not isinstance(grid, dict):
            return []
        rows = grid.get("row", [])
        return rows if isinstance(rows, list) else []

    def _normalize(
        self,
        row: dict,
        market_code: str,
        market_name: str,
        sale_date: str,
        collected_at: str,
    ) -> PriceRecord | None:
        item_name = str(row.get("PUMNM") or row.get("MIDNM") or "").strip()
        if not item_name:
            return None
        item_id = str(row.get("PUMCD") or row.get("MIDCD") or item_name).strip()
        avg = to_int(row.get("COST") or row.get("AVGCOST") or row.get("PRICE"))
        return PriceRecord(
            source="MAFRA",
            item_id=f"MAFRA-{item_id}",
            item_name=item_name,
            category=str(row.get("LARGENM") or "").strip(),
            market_code=market_code,
            market_name=market_name,
            sale_date=sale_date,
            unit=str(row.get("UNIT") or "").strip(),
            avg_price=avg,
            min_price=to_int(row.get("MINCOST"), avg),
            max_price=to_int(row.get("MAXCOST"), avg),
            collected_at=collected_at,
        )
