"""수집 오케스트레이션.

각 소스(MAFRA, KAMIS, KAMIS_CATALOG, SAMPLE)를 실행하여 캐시에 적재하고 로그를 남긴다.
수집 완료 후 알람 체크를 실행한다.
"""

from __future__ import annotations

import logging

from app.cache import store
from app.collectors.base import CollectorError
from app.collectors.kamis import KamisCollector
from app.collectors.kamis_master import KamisMasterCollector
from app.collectors.mafra import MafraCollector
from app.collectors.sample import generate_sample_records
from app.core.config import settings

logger = logging.getLogger(__name__)


async def run_source(source: str) -> dict:
    """단일 소스를 수집하여 캐시에 적재한다.

    Args:
        source: "MAFRA" | "KAMIS" | "KAMIS_CATALOG" | "SAMPLE"

    Returns:
        결과 요약 dict (status, fetched, saved, message).
    """
    source = source.upper()
    log_id = store.start_log(source)
    try:
        if source == "MAFRA":
            records = await MafraCollector(settings.mafra_api_key).collect()
        elif source == "KAMIS":
            records = await KamisCollector(settings.kamis_cert_key, settings.kamis_cert_id).collect()
        elif source == "KAMIS_CATALOG":
            return await _run_catalog_collection(log_id)
        elif source == "SAMPLE":
            records = generate_sample_records()
        else:
            raise CollectorError(f"알 수 없는 소스: {source}")

        saved = store.upsert_price_records(records)
        store.finish_log(log_id, "success", fetched=len(records), saved=saved)
        logger.info("%s 수집 완료: fetched=%d saved=%d", source, len(records), saved)
        return {"status": "success", "source": source, "fetched": len(records), "saved": saved}

    except CollectorError as exc:
        store.finish_log(log_id, "error", message=str(exc))
        logger.warning("%s 수집 실패: %s", source, exc)
        return {"status": "error", "source": source, "message": str(exc)}
    except Exception as exc:  # 방어적: 예기치 못한 오류도 로그로 기록
        store.finish_log(log_id, "error", message=repr(exc))
        logger.exception("%s 수집 중 예외", source)
        return {"status": "error", "source": source, "message": repr(exc)}


async def _run_catalog_collection(log_id: int) -> dict:
    """KAMIS 카탈로그를 수집하여 item_catalog 테이블에 적재한다."""
    collector = KamisMasterCollector(settings.kamis_cert_key, settings.kamis_cert_id)
    catalog_entries = await collector.fetch_catalog()

    # 카탈로그 형태로 변환하여 적재
    items_for_db: list[dict] = []
    for entry in catalog_entries:
        item_code = entry.get("item_code", "")
        category_code = entry.get("category_code", "")
        canonical_id = f"KAMIS-{category_code}-{item_code}-00-00"
        items_for_db.append({
            "source": "KAMIS",
            "item_code": item_code,
            "item_name": entry.get("item_name", ""),
            "kind_code": "",
            "kind_name": "",
            "rank_code": "",
            "rank_name": "",
            "category_code": category_code,
            "category_name": entry.get("category_name", ""),
            "unit": entry.get("unit", ""),
            "canonical_id": canonical_id,
            "latest_price": entry.get("latest_price", 0),
            "price_change_rate": entry.get("price_change_rate", 0.0),
            "price_direction": entry.get("price_direction", ""),
        })

    saved = store.upsert_catalog_items(items_for_db)
    store.finish_log(log_id, "success", fetched=len(catalog_entries), saved=saved)
    logger.info("KAMIS_CATALOG 수집 완료: fetched=%d saved=%d", len(catalog_entries), saved)
    return {"status": "success", "source": "KAMIS_CATALOG", "fetched": len(catalog_entries), "saved": saved}


def available_sources() -> list[str]:
    """설정된 키를 기준으로 활성 가능한 소스 목록을 반환한다."""
    sources: list[str] = []
    if settings.mafra_api_key and settings.mafra_api_key != "sample":
        sources.append("MAFRA")
    if settings.kamis_cert_key:
        sources.append("KAMIS")
        sources.append("KAMIS_CATALOG")
    return sources


async def run_all() -> list[dict]:
    """활성 소스를 모두 수집한 후 알람 체크를 실행한다."""
    sources = available_sources()
    if not sources:
        logger.info("활성 API 키 없음 → 샘플 데이터 수집")
        return [await run_source("SAMPLE")]

    results = [await run_source(s) for s in sources]

    # 수집 완료 후 알람 체크
    try:
        from app.services.alert_checker import check_and_trigger_alerts
        triggered = await check_and_trigger_alerts()
        if triggered:
            logger.info("알람 체크: %d건 새로 트리거됨", triggered)
    except Exception:
        logger.exception("알람 체크 중 오류")

    return results


def ensure_seeded() -> None:
    """캐시가 비어 있고 설정상 허용되면 샘플 데이터를 적재한다."""
    store.init_db()
    if settings.seed_sample_on_empty and store.count_records() == 0:
        records = generate_sample_records()
        store.upsert_price_records(records)
        logger.info("초기 샘플 데이터 %d건 적재", len(records))


def run_sample_sync() -> int:
    """샘플 데이터를 동기적으로 적재한다 (테스트/초기화용). 저장 건수 반환."""
    store.init_db()
    return store.upsert_price_records(generate_sample_records())
