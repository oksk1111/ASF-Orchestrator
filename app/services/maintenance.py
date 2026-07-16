"""정기 유지보수 작업.

- 활동 로그 정리 (30일 보관)
- 오래된 수집 로그 정리
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.cache import store

logger = logging.getLogger(__name__)

ACTIVITY_LOG_RETENTION_DAYS = 30
COLLECTION_LOG_RETENTION_DAYS = 90


def run_maintenance() -> dict[str, int]:
    """유지보수 작업을 실행한다. 삭제된 레코드 수를 반환."""
    results: dict[str, int] = {}

    # 활동 로그 정리
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ACTIVITY_LOG_RETENTION_DAYS)).isoformat()
    deleted = store.cleanup_activity_logs(cutoff)
    results["activity_logs_deleted"] = deleted
    if deleted:
        logger.info("활동 로그 %d건 정리 (보관기간: %d일)", deleted, ACTIVITY_LOG_RETENTION_DAYS)

    # 수집 로그 정리
    cutoff = (datetime.now(timezone.utc) - timedelta(days=COLLECTION_LOG_RETENTION_DAYS)).isoformat()
    deleted = store.cleanup_collection_logs(cutoff)
    results["collection_logs_deleted"] = deleted
    if deleted:
        logger.info("수집 로그 %d건 정리 (보관기간: %d일)", deleted, COLLECTION_LOG_RETENTION_DAYS)

    return results
