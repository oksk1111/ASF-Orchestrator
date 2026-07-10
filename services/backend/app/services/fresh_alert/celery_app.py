from __future__ import annotations

import asyncio
import logging
import os
import time

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery configuration
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery(
    "fresh_alert",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

app.conf.update(
    timezone="Asia/Seoul",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ---------------------------------------------------------------------------
# Beat schedule (all times in KST via Asia/Seoul timezone)
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    "collect_kamis_daily": {
        "task": "app.services.fresh_alert.celery_app.collect_kamis_daily",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "fresh_alert"},
    },
    "collect_mafra_daily": {
        "task": "app.services.fresh_alert.celery_app.collect_mafra_daily",
        "schedule": crontab(hour=6, minute=15),
        "options": {"queue": "fresh_alert"},
    },
    "run_daily_analysis": {
        "task": "app.services.fresh_alert.celery_app.run_daily_analysis",
        "schedule": crontab(hour=6, minute=30),
        "options": {"queue": "fresh_alert"},
    },
    "generate_recommendations": {
        "task": "app.services.fresh_alert.celery_app.generate_recommendations",
        "schedule": crontab(hour=7, minute=0),
        "options": {"queue": "fresh_alert"},
    },
    "check_keyword_alerts_morning": {
        "task": "app.services.fresh_alert.celery_app.check_keyword_alerts",
        "schedule": crontab(hour=7, minute=0),
        "options": {"queue": "fresh_alert"},
    },
    "check_keyword_alerts_noon": {
        "task": "app.services.fresh_alert.celery_app.check_keyword_alerts",
        "schedule": crontab(hour=12, minute=0),
        "options": {"queue": "fresh_alert"},
    },
    "check_keyword_alerts_evening": {
        "task": "app.services.fresh_alert.celery_app.check_keyword_alerts",
        "schedule": crontab(hour=18, minute=0),
        "options": {"queue": "fresh_alert"},
    },
}

# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------


@app.task(name="app.services.fresh_alert.celery_app.collect_kamis_daily", bind=True)
def collect_kamis_daily(self) -> dict:
    """Collect daily price data from KAMIS (Korea Agricultural Marketing Information Service)."""
    logger.info("[collect_kamis_daily] Starting KAMIS data collection")
    start = time.time()
    try:
        from app.services.fresh_alert.pipeline import collect_kamis_data

        result = asyncio.run(collect_kamis_data())
        elapsed = time.time() - start
        logger.info("[collect_kamis_daily] Completed in %.2fs", elapsed)
        return {"status": "success", "elapsed_seconds": round(elapsed, 2), "result": result}
    except Exception as exc:
        elapsed = time.time() - start
        logger.exception("[collect_kamis_daily] Failed after %.2fs: %s", elapsed, exc)
        return {"status": "error", "elapsed_seconds": round(elapsed, 2), "error": str(exc)}


@app.task(name="app.services.fresh_alert.celery_app.collect_mafra_daily", bind=True)
def collect_mafra_daily(self) -> dict:
    """Collect daily data from MAFRA (Ministry of Agriculture, Food and Rural Affairs)."""
    logger.info("[collect_mafra_daily] Starting MAFRA data collection")
    start = time.time()
    try:
        from app.services.fresh_alert.pipeline import collect_mafra_data

        result = asyncio.run(collect_mafra_data())
        elapsed = time.time() - start
        logger.info("[collect_mafra_daily] Completed in %.2fs", elapsed)
        return {"status": "success", "elapsed_seconds": round(elapsed, 2), "result": result}
    except Exception as exc:
        elapsed = time.time() - start
        logger.exception("[collect_mafra_daily] Failed after %.2fs: %s", elapsed, exc)
        return {"status": "error", "elapsed_seconds": round(elapsed, 2), "error": str(exc)}


@app.task(name="app.services.fresh_alert.celery_app.run_daily_analysis", bind=True)
def run_daily_analysis(self) -> dict:
    """Run daily price trend analysis and anomaly detection."""
    logger.info("[run_daily_analysis] Starting daily analysis")
    start = time.time()
    try:
        from app.services.fresh_alert.pipeline import run_analysis

        result = asyncio.run(run_analysis())
        elapsed = time.time() - start
        logger.info("[run_daily_analysis] Completed in %.2fs", elapsed)
        return {"status": "success", "elapsed_seconds": round(elapsed, 2), "result": result}
    except Exception as exc:
        elapsed = time.time() - start
        logger.exception("[run_daily_analysis] Failed after %.2fs: %s", elapsed, exc)
        return {"status": "error", "elapsed_seconds": round(elapsed, 2), "error": str(exc)}


@app.task(name="app.services.fresh_alert.celery_app.generate_recommendations", bind=True)
def generate_recommendations(self) -> dict:
    """Generate purchase recommendations based on analysis results."""
    logger.info("[generate_recommendations] Starting recommendation generation")
    start = time.time()
    try:
        from app.services.fresh_alert.pipeline import generate_recommendations as _generate

        result = asyncio.run(_generate())
        elapsed = time.time() - start
        logger.info("[generate_recommendations] Completed in %.2fs", elapsed)
        return {"status": "success", "elapsed_seconds": round(elapsed, 2), "result": result}
    except Exception as exc:
        elapsed = time.time() - start
        logger.exception("[generate_recommendations] Failed after %.2fs: %s", elapsed, exc)
        return {"status": "error", "elapsed_seconds": round(elapsed, 2), "error": str(exc)}


@app.task(name="app.services.fresh_alert.celery_app.check_keyword_alerts", bind=True)
def check_keyword_alerts(self) -> dict:
    """Check keyword-based alert conditions and notify subscribed users."""
    logger.info("[check_keyword_alerts] Starting keyword alert check")
    start = time.time()
    try:
        from app.services.fresh_alert.pipeline import check_keyword_alerts as _check

        result = asyncio.run(_check())
        elapsed = time.time() - start
        logger.info("[check_keyword_alerts] Completed in %.2fs", elapsed)
        return {"status": "success", "elapsed_seconds": round(elapsed, 2), "result": result}
    except Exception as exc:
        elapsed = time.time() - start
        logger.exception("[check_keyword_alerts] Failed after %.2fs: %s", elapsed, exc)
        return {"status": "error", "elapsed_seconds": round(elapsed, 2), "error": str(exc)}
