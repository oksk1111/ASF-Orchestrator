from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
    }
