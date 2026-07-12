"""ASF-Orchestrator 중간 서버 진입점.

- 소비자용 API (/api/v1/...)
- 관리자 웹 (/admin)
- 시작 시 캐시 초기화 + (선택) 주기적 자동 수집
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
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


async def _scheduler() -> None:
    """주기적으로 활성 소스를 수집한다 (COLLECT_INTERVAL_HOURS > 0 일 때)."""
    interval = settings.collect_interval_hours * 3600
    while True:
        try:
            await asyncio.sleep(interval)
            logger.info("스케줄 수집 시작")
            await ingest.run_all()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("스케줄 수집 중 오류")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 수명주기: 캐시 초기화 + 백그라운드 스케줄러."""
    ingest.ensure_seeded()
    task: asyncio.Task | None = None
    if settings.collect_interval_hours > 0:
        task = asyncio.create_task(_scheduler())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
