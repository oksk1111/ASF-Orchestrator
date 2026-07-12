"""헬스체크 라우트."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.cache import store
from app.core.config import settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """서비스 상태와 캐시 레코드 수를 반환한다."""
    try:
        count = store.count_records()
    except Exception:
        count = 0
    return HealthResponse(app=settings.app_name, version=__version__, cache_records=count)
