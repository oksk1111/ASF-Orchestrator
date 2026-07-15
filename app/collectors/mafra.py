"""MAFRA(농림축산식품 공공데이터 포털, data.mafra.go.kr) OpenAPI 수집기.

엔드포인트: http://211.237.50.150:7080/openapi/{apiKey}/json/{gridId}/{start}/{end}
(참고: data.go.kr이 아니라 별도 포털인 data.mafra.go.kr 소속 API. API마다 개별
"오픈API 사용신청"이 필요하며 신청 IP가 등록되어 있어야 한다.)

이 서버 계정으로 실제 사용 승인된(신청 완료) API 중 실데이터가 확인된 2개를
수집한다 (2026-07-15 실제 호출로 파라미터/필드 확인됨):

- 농수축산물 도매가격 (Grid_20150406000000000217_1) — 파라미터 EXAMIN_DE(YYYYMMDD)
- 농수축산물 소매가격 (Grid_20141225000000000163_1) — 파라미터 EXAMIN_DE(YYYYMMDD)

주의:
- 기존에 사용하던 "도매시장 정산 가격 정보"(Grid_20240625000000000653_1)는
  이 계정으로 사용신청이 되어있지 않아 INFO-100(인증키 유효하지 않음) 오류가 발생하므로
  더 이상 호출하지 않는다.
- "도매시장 산지공판장 정산 가격"(Grid_20240625000000000660_1)도 신청되어 있으나,
  인증은 정상이나 테스트 기간 동안 조회된 데이터가 계속 0건이라 당장 필요하지 않아
  수집 대상에서 제외했다. 추후 필요해지면 다시 추가할 것.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.collectors.base import CollectorError, to_int
from app.models.schemas import PriceRecord

logger = logging.getLogger(__name__)

MAFRA_BASE_URL = "http://211.237.50.150:7080/openapi"

WHOLESALE_PRICE = "Grid_20150406000000000217_1"  # 농수축산물 도매가격
RETAIL_PRICE = "Grid_20141225000000000163_1"  # 농수축산물 소매가격

_PAGE_SIZE = 1000


def _kst_yesterday() -> str:
    """KST 기준 어제 날짜(YYYYMMDD)."""
    now = datetime.now(timezone.utc) + timedelta(hours=9)
    return (now - timedelta(days=1)).strftime("%Y%m%d")


class MafraCollector:
    """MAFRA 도매/소매가격 + 산지공판장 정산가격 수집기."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def collect(self, sale_date: str | None = None) -> list[PriceRecord]:
        """지정일(없으면 어제)의 도매/소매가격을 수집한다.

        Raises:
            CollectorError: 인증/네트워크/파싱 오류.
        """
        date = sale_date or _kst_yesterday()
        collected_at = datetime.now(timezone.utc).isoformat()
        records: list[PriceRecord] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            wholesale_rows = await self._fetch_all(client, WHOLESALE_PRICE, {"EXAMIN_DE": date})
            for row in wholesale_rows:
                rec = self._normalize_examin(row, "도매", collected_at)
                if rec is not None:
                    records.append(rec)

            retail_rows = await self._fetch_all(client, RETAIL_PRICE, {"EXAMIN_DE": date})
            for row in retail_rows:
                rec = self._normalize_examin(row, "소매", collected_at)
                if rec is not None:
                    records.append(rec)

        return records

    async def _fetch_all(
        self, client: httpx.AsyncClient, grid: str, params: dict[str, str]
    ) -> list[dict]:
        """{start}/{end} 행 범위를 페이지네이션하며 전체 결과를 수집한다."""
        rows: list[dict] = []
        start = 1
        while True:
            end = start + _PAGE_SIZE - 1
            url = f"{MAFRA_BASE_URL}/{self.api_key}/json/{grid}/{start}/{end}"
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                raise CollectorError(f"MAFRA HTTP 오류: {exc}") from exc
            except ValueError as exc:
                raise CollectorError(f"MAFRA 응답 파싱 오류: {exc}") from exc

            result = data.get("result")
            if isinstance(result, dict):
                code = str(result.get("code", ""))
                if code and code != "INFO-000":
                    raise CollectorError(f"MAFRA 오류 {code}: {result.get('message', '')}")

            body = data.get(grid)
            if not isinstance(body, dict):
                break
            page_rows = body.get("row", [])
            if not isinstance(page_rows, list):
                break
            rows.extend(page_rows)

            total = to_int(body.get("totalCnt"))
            if not page_rows or len(rows) >= total or len(page_rows) < _PAGE_SIZE:
                break
            start = end + 1
        return rows

    def _normalize_examin(self, row: dict, kind: str, collected_at: str) -> PriceRecord | None:
        """농수축산물 도매가격/소매가격(EXAMIN_DE 계열) 레코드를 정규화한다."""
        item_name = str(row.get("PRDLST_NM") or "").strip()
        if not item_name:
            return None
        species = str(row.get("SPCIES_NM") or "").strip()
        full_name = f"{item_name}({species})" if species and species != item_name else item_name

        item_id = "-".join(
            part
            for part in (
                "MAFRA",
                kind,
                str(row.get("PRDLST_CD") or ""),
                str(row.get("SPCIES_CD") or ""),
                str(row.get("GRAD_CD") or ""),
            )
            if part
        )
        price = to_int(row.get("AMT"))
        return PriceRecord(
            source="MAFRA",
            item_id=item_id,
            item_name=full_name,
            category=str(row.get("FRMPRD_CATGORY_NM") or "").strip(),
            market_code=str(row.get("MRKT_CD") or "").strip(),
            market_name=str(row.get("MRKT_NM") or "").strip(),
            sale_date=str(row.get("EXAMIN_DE") or "").strip(),
            unit=str(row.get("EXAMIN_UNIT") or "").strip(),
            avg_price=price,
            min_price=price,
            max_price=price,
            collected_at=collected_at,
        )
