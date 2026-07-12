"""관리자 웹 UI 라우트 (HTTP Basic 보호).

- GET  /admin          : 대시보드 (소스 상태, 캐시 요약, 최근 로그)
- POST /admin/collect  : 수집 실행 (source=SAMPLE|MAFRA|KAMIS|ALL)
- GET  /admin/prices   : 캐시 레코드 브라우징
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.cache import store
from app.core.config import settings
from app.core.security import require_admin
from app.services import ingest

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(prefix="/admin", tags=["Admin"])


def _source_status() -> list[dict]:
    """설정된 키 기준 소스 활성 상태."""
    return [
        {
            "name": "MAFRA",
            "configured": bool(settings.mafra_api_key and settings.mafra_api_key != "sample"),
            "desc": "농림축산식품부 도매시장 통합 OpenAPI",
        },
        {
            "name": "KAMIS",
            "configured": bool(settings.kamis_service_key),
            "desc": "data.go.kr 일별 도·소매 가격 (B552845/perDay)",
        },
        {
            "name": "SAMPLE",
            "configured": True,
            "desc": "내장 샘플 데이터 (키 불필요)",
        },
    ]


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, _: str = Depends(require_admin), msg: str | None = None):
    """관리자 대시보드."""
    context = {
        "request": request,
        "app_name": settings.app_name,
        "total_records": store.count_records(),
        "summaries": store.source_summaries(),
        "logs": store.recent_logs(limit=15),
        "sources": _source_status(),
        "msg": msg,
    }
    return templates.TemplateResponse(request, "dashboard.html", context)


@router.post("/collect")
async def collect(source: str = Form(...), _: str = Depends(require_admin)):
    """수집을 실행하고 대시보드로 리다이렉트한다 (PRG)."""
    source = source.upper()
    if source == "ALL":
        results = await ingest.run_all()
        saved = sum(r.get("saved", 0) for r in results)
        errors = [r["message"] for r in results if r.get("status") == "error"]
        msg = f"전체 수집 완료 — 저장 {saved}건" + (f", 오류 {len(errors)}건" if errors else "")
    else:
        result = await ingest.run_source(source)
        if result.get("status") == "success":
            msg = f"{source} 수집 완료 — 저장 {result.get('saved', 0)}건"
        else:
            msg = f"{source} 수집 실패 — {result.get('message', '')}"
    return RedirectResponse(url=f"/admin?msg={msg}", status_code=303)


@router.get("/prices", response_class=HTMLResponse)
def prices(request: Request, _: str = Depends(require_admin), source: str | None = None):
    """캐시 레코드 브라우징."""
    records = store.query_prices(source=source, limit=200)
    context = {
        "request": request,
        "app_name": settings.app_name,
        "records": records,
        "source": source or "전체",
    }
    return templates.TemplateResponse(request, "prices.html", context)
