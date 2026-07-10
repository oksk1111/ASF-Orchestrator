"""MAFRA (농림축산식품부) public API data collector for FreshAlert.

Fetches real-time auction data, settlement prices, and market volume
information from the MAFRA open data portal.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAFRA_BASE_URL = "http://211.237.50.150:7080/openapi"

# Grid IDs for each API endpoint
REALTIME_AUCTION = "Grid_20240625000000000654_1"
SETTLEMENT_PRICE = "Grid_20240625000000000653_1"
RAW_SETTLEMENT = "Grid_20240625000000000655_1"
MARKET_ITEM_VOLUME = "Grid_20240625000000000658_1"
MARKET_TOTAL_VOLUME = "Grid_20240625000000000656_1"
CORP_ITEM_VOLUME = "Grid_20240625000000000659_1"
MARKET_CODES = "Grid_20240625000000000661_1"
CORP_CODES = "Grid_20240626000000000662_1"


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class MafraCollector:
    """Async data collector for MAFRA open APIs.

    Provides methods to fetch real-time auction results, settlement prices,
    and market volume data from the MAFRA (농림축산식품부) public data portal.
    """

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _fetch(
        self,
        grid_id: str,
        start: int,
        end: int,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Generic fetch from MAFRA API.

        Builds the URL using the grid_id and pagination range, appends any
        extra query parameters, and returns the 'row' list from the response.

        Args:
            grid_id: The MAFRA grid identifier for the target dataset.
            start: Start index for pagination (1-based).
            end: End index for pagination.
            params: Optional query parameters to filter results.

        Returns:
            List of row dicts from the API response, or empty list on error.
        """
        url = f"{MAFRA_BASE_URL}/{self.api_key}/json/{grid_id}/{start}/{end}"

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # MAFRA API wraps results under the grid_id key
            grid_data = data.get(grid_id)
            if grid_data is None:
                logger.warning("No grid data found in response for %s", grid_id)
                return []

            return grid_data.get("row", [])

        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP %d from MAFRA API (grid=%s): %s",
                exc.response.status_code,
                grid_id,
                exc.response.text[:200],
            )
            return []
        except httpx.RequestError as exc:
            logger.error("Request error for MAFRA API (grid=%s): %s", grid_id, exc)
            return []
        except (KeyError, ValueError) as exc:
            logger.error("Failed to parse MAFRA response (grid=%s): %s", grid_id, exc)
            return []

    async def fetch_realtime_auction(
        self,
        sale_date: str,
        market_code: str,
        large: str | None = None,
        mid: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch real-time auction data for a given date and market.

        Args:
            sale_date: Auction date in YYYYMMDD format.
            market_code: Wholesale market code.
            large: Optional large category code to filter by.
            mid: Optional mid category code to filter by.

        Returns:
            List of auction record dicts.
        """
        params: dict[str, str] = {
            "SALEDATE": sale_date,
            "WHSALCD": market_code,
        }
        if large is not None:
            params["LARGECD"] = large
        if mid is not None:
            params["MIDCD"] = mid

        return await self._fetch(REALTIME_AUCTION, 1, 1000, params)

    async def fetch_settlement_price(
        self,
        sale_date: str,
        market_code: str,
    ) -> list[dict[str, Any]]:
        """Fetch settlement (정산) prices for a given date and market.

        Args:
            sale_date: Settlement date in YYYYMMDD format.
            market_code: Wholesale market code.

        Returns:
            List of settlement price record dicts.
        """
        params: dict[str, str] = {
            "SALEDATE": sale_date,
            "WHSALCD": market_code,
        }
        return await self._fetch(SETTLEMENT_PRICE, 1, 1000, params)

    async def fetch_market_item_volume(
        self,
        regist_date: str,
        market_code: str | None = None,
        large: str | None = None,
        mid: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch per-item volume data for a market on a given date.

        Args:
            regist_date: Registration date in YYYYMMDD format.
            market_code: Optional market code to filter.
            large: Optional large category code.
            mid: Optional mid category code.

        Returns:
            List of item volume record dicts.
        """
        params: dict[str, str] = {"REGISTDATE": regist_date}
        if market_code is not None:
            params["WHSALCD"] = market_code
        if large is not None:
            params["LARGECD"] = large
        if mid is not None:
            params["MIDCD"] = mid

        return await self._fetch(MARKET_ITEM_VOLUME, 1, 1000, params)

    async def fetch_market_total_volume(
        self,
        regist_date: str,
        market_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch total volume data for a market on a given date.

        Args:
            regist_date: Registration date in YYYYMMDD format.
            market_code: Optional market code to filter.

        Returns:
            List of total volume record dicts.
        """
        params: dict[str, str] = {"REGISTDATE": regist_date}
        if market_code is not None:
            params["WHSALCD"] = market_code

        return await self._fetch(MARKET_TOTAL_VOLUME, 1, 1000, params)

    async def fetch_market_codes(self) -> list[dict[str, Any]]:
        """Fetch the list of wholesale market codes.

        Returns:
            List of market code record dicts.
        """
        return await self._fetch(MARKET_CODES, 1, 500, None)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()


# ---------------------------------------------------------------------------
# Record parsers
# ---------------------------------------------------------------------------


def parse_auction_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Map raw MAFRA auction API field names to internal field names.

    Args:
        raw: A single row dict from the real-time auction API response.

    Returns:
        Dict with normalized field names for internal use.
    """
    return {
        "sale_date": raw.get("SALEDATE", ""),
        "market_code": raw.get("WHSALCD", ""),
        "market_name": raw.get("WHSALNAME", ""),
        "corp_name": raw.get("CMPNAME", ""),
        "large_name": raw.get("LARGENAME", ""),
        "mid_name": raw.get("MIDNAME", ""),
        "small_name": raw.get("SMALLNAME", ""),
        "origin": raw.get("SANNAME", ""),
        "cost": int(raw.get("COST", 0) or 0),
        "qty": int(raw.get("QTY", 0) or 0),
        "grade": raw.get("STD", ""),
        "auction_time": raw.get("SBIDTIME", ""),
    }


def parse_settlement_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Map raw MAFRA settlement API field names to internal field names.

    Args:
        raw: A single row dict from the settlement price API response.

    Returns:
        Dict with normalized field names for internal use.
    """
    return {
        "sale_date": raw.get("SALEDATE", ""),
        "market_code": raw.get("WHSALCD", ""),
        "market_name": raw.get("WHSALNAME", ""),
        "large_name": raw.get("LARGENAME", ""),
        "mid_name": raw.get("MIDNAME", ""),
        "small_name": raw.get("SMALLNAME", ""),
        "avg_price": int(raw.get("AVGAMT", 0) or 0),
        "min_price": int(raw.get("MINAMT", 0) or 0),
        "max_price": int(raw.get("MAXAMT", 0) or 0),
        "total_qty": int(raw.get("TOTQTY", 0) or 0),
        "total_amt": int(raw.get("TOTAMT", 0) or 0),
    }
