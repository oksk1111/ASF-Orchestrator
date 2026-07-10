from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import perf_counter, time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.routes import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(api_router, prefix="/api/v1")

_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = Lock()
_metrics_lock = Lock()
_metrics = {
    "requests_total": 0,
    "requests_2xx": 0,
    "requests_4xx": 0,
    "requests_5xx": 0,
    "latency_seconds_sum": 0.0,
    "latency_seconds_count": 0,
}


@app.middleware("http")
async def rate_limit_and_metrics(request: Request, call_next):
    started = perf_counter()
    client_ip = request.client.host if request.client else "unknown"

    now_ts = time()
    with _rate_lock:
        bucket = _rate_buckets[client_ip]
        while bucket and now_ts - bucket[0] > 60.0:
            bucket.popleft()

        if len(bucket) >= settings.rate_limit_per_minute:
            with _metrics_lock:
                _metrics["requests_total"] += 1
                _metrics["requests_4xx"] += 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests"},
            )

        bucket.append(now_ts)

    response = await call_next(request)

    elapsed = perf_counter() - started
    with _metrics_lock:
        _metrics["requests_total"] += 1
        _metrics["latency_seconds_sum"] += elapsed
        _metrics["latency_seconds_count"] += 1
        if 200 <= response.status_code < 300:
            _metrics["requests_2xx"] += 1
        elif 400 <= response.status_code < 500:
            _metrics["requests_4xx"] += 1
        elif response.status_code >= 500:
            _metrics["requests_5xx"] += 1

    return response


@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/api/v1/healthz",
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    with _metrics_lock:
        avg_latency = 0.0
        if _metrics["latency_seconds_count"] > 0:
            avg_latency = _metrics["latency_seconds_sum"] / _metrics["latency_seconds_count"]

        lines = [
            "# HELP http_requests_total Total HTTP requests",
            "# TYPE http_requests_total counter",
            f"http_requests_total {_metrics['requests_total']}",
            f"http_requests_2xx_total {_metrics['requests_2xx']}",
            f"http_requests_4xx_total {_metrics['requests_4xx']}",
            f"http_requests_5xx_total {_metrics['requests_5xx']}",
            "# HELP http_request_latency_seconds_avg Average latency",
            "# TYPE http_request_latency_seconds_avg gauge",
            f"http_request_latency_seconds_avg {avg_latency:.6f}",
        ]
    return PlainTextResponse("\n".join(lines) + "\n")
