"""SQLite 기반 캐시 저장소.

정규화된 가격 레코드와 수집 로그를 저장/조회한다.
저volume 사용을 가정하여 작업마다 커넥션을 열고 닫는다.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.schemas import CollectionLog, PriceRecord, SourceSummary

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    item_id      TEXT NOT NULL,
    item_name    TEXT NOT NULL,
    category     TEXT DEFAULT '',
    market_code  TEXT DEFAULT '',
    market_name  TEXT DEFAULT '',
    sale_date    TEXT NOT NULL,
    unit         TEXT DEFAULT '',
    avg_price    INTEGER DEFAULT 0,
    min_price    INTEGER DEFAULT 0,
    max_price    INTEGER DEFAULT 0,
    collected_at TEXT DEFAULT '',
    UNIQUE(source, item_id, market_code, sale_date)
);
CREATE INDEX IF NOT EXISTS idx_price_item ON price_records(item_id, sale_date);
CREATE INDEX IF NOT EXISTS idx_price_source ON price_records(source);

CREATE TABLE IF NOT EXISTS collection_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,
    status      TEXT NOT NULL,
    fetched     INTEGER DEFAULT 0,
    saved       INTEGER DEFAULT 0,
    message     TEXT DEFAULT '',
    started_at  TEXT NOT NULL,
    finished_at TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    path: Path = settings.cache_db_abspath
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """스키마를 생성한다 (멱등)."""
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ─── 가격 레코드 ──────────────────────────────────────────────────────────────


def upsert_price_records(records: list[PriceRecord]) -> int:
    """가격 레코드를 upsert 한다. 저장(신규+갱신)된 건수를 반환."""
    if not records:
        return 0
    conn = _connect()
    try:
        cur = conn.cursor()
        for r in records:
            collected = r.collected_at or _now_iso()
            cur.execute(
                """
                INSERT INTO price_records
                    (source, item_id, item_name, category, market_code, market_name,
                     sale_date, unit, avg_price, min_price, max_price, collected_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source, item_id, market_code, sale_date) DO UPDATE SET
                    item_name=excluded.item_name,
                    category=excluded.category,
                    market_name=excluded.market_name,
                    unit=excluded.unit,
                    avg_price=excluded.avg_price,
                    min_price=excluded.min_price,
                    max_price=excluded.max_price,
                    collected_at=excluded.collected_at
                """,
                (
                    r.source, r.item_id, r.item_name, r.category, r.market_code,
                    r.market_name, r.sale_date, r.unit, r.avg_price, r.min_price,
                    r.max_price, collected,
                ),
            )
        conn.commit()
        return len(records)
    finally:
        conn.close()


def query_prices(
    item_id: str | None = None,
    source: str | None = None,
    limit: int = 100,
) -> list[PriceRecord]:
    """가격 레코드를 조회한다 (최신순)."""
    clauses: list[str] = []
    params: list[object] = []
    if item_id:
        clauses.append("item_id = ?")
        params.append(item_id)
    if source:
        clauses.append("source = ?")
        params.append(source)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM price_records {where} "
            f"ORDER BY sale_date DESC, id DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_price(r) for r in rows]
    finally:
        conn.close()


def latest_prices(limit: int = 50) -> list[PriceRecord]:
    """가장 최근 수집된 레코드를 반환한다."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM price_records ORDER BY sale_date DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_price(r) for r in rows]
    finally:
        conn.close()


def count_records() -> int:
    conn = _connect()
    try:
        return int(conn.execute("SELECT COUNT(*) AS c FROM price_records").fetchone()["c"])
    finally:
        conn.close()


def source_summaries() -> list[SourceSummary]:
    """소스별 캐시 요약을 반환한다."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT source,
                   COUNT(*) AS cnt,
                   MAX(sale_date) AS latest_sale,
                   MAX(collected_at) AS last_collected
            FROM price_records GROUP BY source ORDER BY source
            """
        ).fetchall()
        return [
            SourceSummary(
                source=r["source"],
                record_count=int(r["cnt"]),
                latest_sale_date=r["latest_sale"],
                last_collected_at=r["last_collected"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def _row_to_price(r: sqlite3.Row) -> PriceRecord:
    return PriceRecord(
        source=r["source"],
        item_id=r["item_id"],
        item_name=r["item_name"],
        category=r["category"] or "",
        market_code=r["market_code"] or "",
        market_name=r["market_name"] or "",
        sale_date=r["sale_date"],
        unit=r["unit"] or "",
        avg_price=r["avg_price"] or 0,
        min_price=r["min_price"] or 0,
        max_price=r["max_price"] or 0,
        collected_at=r["collected_at"] or "",
    )


# ─── 수집 로그 ────────────────────────────────────────────────────────────────


def start_log(source: str) -> int:
    """수집 시작 로그를 남기고 로그 id를 반환한다."""
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO collection_logs (source, status, started_at) VALUES (?, 'running', ?)",
            (source, _now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def finish_log(
    log_id: int,
    status: str,
    fetched: int = 0,
    saved: int = 0,
    message: str = "",
) -> None:
    """수집 종료 로그를 갱신한다."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE collection_logs SET status=?, fetched=?, saved=?, message=?, finished_at=? "
            "WHERE id=?",
            (status, fetched, saved, message[:500], _now_iso(), log_id),
        )
        conn.commit()
    finally:
        conn.close()


def recent_logs(limit: int = 20) -> list[CollectionLog]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM collection_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            CollectionLog(
                id=r["id"],
                source=r["source"],
                status=r["status"],
                fetched=r["fetched"] or 0,
                saved=r["saved"] or 0,
                message=r["message"] or "",
                started_at=r["started_at"],
                finished_at=r["finished_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()
