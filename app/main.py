"""ASF-Orchestrator 중간 서버 진입점.

- 소비자용 API (/api/v1/...)
- 관리자 웹 (/admin)
- 시작 시 캐시 초기화 + 즉시 수집 + 주기적 자동 수집
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.admin.router import router as admin_router
from app.api.routes import api_router
from app.core.config import settings
from app.services import ingest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "admin" / "static"
_KST = timezone(timedelta(hours=9))


def _parse_collect_times() -> list[tuple[int, int]]:
    """collect_times_kst 설정을 파싱하여 (hour, minute) 목록을 반환한다."""
    times: list[tuple[int, int]] = []
    raw = settings.collect_times_kst.strip()
    if not raw:
        return times
    for part in raw.split(","):
        part = part.strip()
        if ":" in part:
            h, m = part.split(":", 1)
            times.append((int(h), int(m)))
    return times


def _seconds_until_next_time(times: list[tuple[int, int]]) -> int:
    """다음 수집 시각까지 남은 초를 계산한다 (KST 기준)."""
    now = datetime.now(_KST)
    candidates: list[float] = []
    for h, m in times:
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        candidates.append((target - now).total_seconds())
    return int(min(candidates)) if candidates else settings.collect_interval_hours * 3600


async def _scheduler() -> None:
    """시작 즉시 수집 후, 설정된 시각/간격에 따라 주기적으로 수집한다."""
    # 시작 즉시 1회 수집
    try:
        logger.info("서버 시작 수집 실행")
        await ingest.run_all()
    except Exception:
        logger.exception("시작 수집 중 오류")

    collect_times = _parse_collect_times()

    while True:
        try:
            if collect_times:
                delay = _seconds_until_next_time(collect_times)
                logger.info("다음 수집까지 %d초 (KST %s)", delay, settings.collect_times_kst)
            else:
                delay = settings.collect_interval_hours * 3600
                logger.info("다음 수집까지 %d시간", settings.collect_interval_hours)
            await asyncio.sleep(delay)
            logger.info("스케줄 수집 시작")
            await ingest.run_all()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("스케줄 수집 중 오류")


async def _maintenance_scheduler() -> None:
    """매일 03:00 KST에 유지보수 작업(로그 정리 등)을 실행한다."""
    while True:
        try:
            now = datetime.now(_KST)
            target = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            await asyncio.sleep((target - now).total_seconds())

            from app.services.maintenance import run_maintenance
            logger.info("유지보수 작업 시작")
            run_maintenance()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("유지보수 작업 중 오류")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 수명주기: 캐시 초기화 + 백그라운드 스케줄러."""
    ingest.ensure_seeded()
    tasks: list[asyncio.Task] = []
    if settings.collect_interval_hours > 0 or settings.collect_times_kst.strip():
        tasks.append(asyncio.create_task(_scheduler()))
    tasks.append(asyncio.create_task(_maintenance_scheduler()))
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    # 로컬 개발: localhost/127.0.0.1 임의 포트 + Vercel 프리뷰 도메인
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 활동 로그 미들웨어 등록
from app.middleware.activity_log import ActivityLogMiddleware  # noqa: E402

app.add_middleware(ActivityLogMiddleware)

app.mount("/admin/static", StaticFiles(directory=str(_STATIC_DIR)), name="admin-static")
app.include_router(admin_router)
app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root():
    return {
        "service": settings.app_name,
        "version": __version__,
        "admin": "/admin",
        "docs": "/docs",
        "health": "/healthz",
    }
