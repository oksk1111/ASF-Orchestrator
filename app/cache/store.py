"""SQLite 기반 캐시 저장소.

정규화된 가격 레코드, 수집 로그, 알람, 사용자, 활동 로그를 저장/조회한다.
저volume 사용을 가정하여 작업마다 커넥션을 열고 닫는다.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import settings
from app.models.schemas import (
    ActivityLog,
    AlertTrigger,
    CatalogItem,
    CollectionLog,
    PriceAlert,
    PriceRecord,
    SourceSummary,
    User,
)

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

CREATE TABLE IF NOT EXISTS price_alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT NOT NULL,
    item_id       TEXT NOT NULL,
    item_name     TEXT DEFAULT '',
    target_price  INTEGER NOT NULL,
    direction     TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alert_user ON price_alerts(user_id);

CREATE TABLE IF NOT EXISTS alert_triggers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id     INTEGER NOT NULL,
    user_id      TEXT NOT NULL,
    item_id      TEXT NOT NULL,
    item_name    TEXT DEFAULT '',
    target_price INTEGER NOT NULL,
    actual_price INTEGER NOT NULL,
    direction    TEXT NOT NULL,
    triggered_at TEXT NOT NULL,
    pushed_at    TEXT,
    read_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_trigger_user ON alert_triggers(user_id, read_at);
CREATE INDEX IF NOT EXISTS idx_trigger_alert ON alert_triggers(alert_id, triggered_at);

CREATE TABLE IF NOT EXISTS user_devices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      TEXT NOT NULL,
    fcm_token    TEXT NOT NULL,
    device_name  TEXT DEFAULT '',
    platform     TEXT DEFAULT '',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    UNIQUE(user_id, fcm_token)
);
CREATE INDEX IF NOT EXISTS idx_device_user ON user_devices(user_id);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    google_id       TEXT UNIQUE NOT NULL,
    email           TEXT NOT NULL,
    name            TEXT NOT NULL DEFAULT '',
    profile_image   TEXT DEFAULT '',
    role            TEXT NOT NULL DEFAULT 'user',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    last_login_at   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_google ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);

CREATE TABLE IF NOT EXISTS item_catalog (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL DEFAULT 'KAMIS',
    item_code       TEXT NOT NULL,
    item_name       TEXT NOT NULL,
    kind_code       TEXT DEFAULT '',
    kind_name       TEXT DEFAULT '',
    rank_code       TEXT DEFAULT '',
    rank_name       TEXT DEFAULT '',
    category_code   TEXT NOT NULL,
    category_name   TEXT DEFAULT '',
    unit            TEXT DEFAULT '',
    canonical_id    TEXT NOT NULL,
    latest_price    INTEGER DEFAULT 0,
    price_change_rate REAL DEFAULT 0,
    price_direction TEXT DEFAULT '',
    updated_at      TEXT NOT NULL,
    UNIQUE(source, item_code, kind_code, rank_code)
);
CREATE INDEX IF NOT EXISTS idx_catalog_canonical ON item_catalog(canonical_id);
CREATE INDEX IF NOT EXISTS idx_catalog_name ON item_catalog(item_name);
CREATE INDEX IF NOT EXISTS idx_catalog_category ON item_catalog(category_code);

CREATE TABLE IF NOT EXISTS activity_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT,
    user_email  TEXT DEFAULT '',
    action      TEXT NOT NULL,
    detail      TEXT DEFAULT '',
    ip_address  TEXT DEFAULT '',
    user_agent  TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_date ON activity_logs(created_at);
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


def cleanup_collection_logs(cutoff_iso: str) -> int:
    """지정 시각 이전의 수집 로그를 삭제한다."""
    conn = _connect()
    try:
        cur = conn.execute(
            "DELETE FROM collection_logs WHERE started_at < ?", (cutoff_iso,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ─── 가격 알람 ────────────────────────────────────────────────────────────────


def create_alert(alert: PriceAlert) -> PriceAlert:
    """가격 알람을 등록한다. id/created_at이 채워진 레코드를 반환."""
    created_at = alert.created_at or _now_iso()
    conn = _connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO price_alerts
                (user_id, item_id, item_name, target_price, direction, active, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                alert.user_id, alert.item_id, alert.item_name, alert.target_price,
                alert.direction, int(alert.active), created_at,
            ),
        )
        conn.commit()
        return alert.model_copy(update={"id": int(cur.lastrowid), "created_at": created_at})
    finally:
        conn.close()


def list_alerts(user_id: str) -> list[PriceAlert]:
    """사용자의 가격 알람 목록을 반환한다."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM price_alerts WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
        return [_row_to_alert(r) for r in rows]
    finally:
        conn.close()


def get_alert(alert_id: int) -> PriceAlert | None:
    """알람 id로 단건 조회한다."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM price_alerts WHERE id=?", (alert_id,)
        ).fetchone()
        return _row_to_alert(row) if row else None
    finally:
        conn.close()


def get_all_active_alerts() -> list[PriceAlert]:
    """모든 활성 알람을 반환한다 (alert_checker에서 사용)."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM price_alerts WHERE active=1 ORDER BY id"
        ).fetchall()
        return [_row_to_alert(r) for r in rows]
    finally:
        conn.close()


def delete_alert(alert_id: int, user_id: str) -> bool:
    """본인 소유 알람을 삭제한다. 삭제되면 True."""
    conn = _connect()
    try:
        cur = conn.execute(
            "DELETE FROM price_alerts WHERE id=? AND user_id=?", (alert_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def latest_price_for_item(item_id: str) -> int | None:
    """품목의 가장 최근 평균가를 반환한다 (여러 시장이 있으면 평균)."""
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT AVG(avg_price) AS avg_price FROM price_records
            WHERE item_id=? AND sale_date=(
                SELECT MAX(sale_date) FROM price_records WHERE item_id=? AND avg_price > 0
            ) AND avg_price > 0
            """,
            (item_id, item_id),
        ).fetchone()
        return int(row["avg_price"]) if row and row["avg_price"] is not None else None
    finally:
        conn.close()


def _row_to_alert(r: sqlite3.Row) -> PriceAlert:
    return PriceAlert(
        id=r["id"],
        user_id=r["user_id"],
        item_id=r["item_id"],
        item_name=r["item_name"] or "",
        target_price=r["target_price"],
        direction=r["direction"],
        active=bool(r["active"]),
        created_at=r["created_at"],
    )


# ─── 알람 트리거 ──────────────────────────────────────────────────────────────


def alert_triggered_today(alert_id: int) -> bool:
    """해당 알람이 오늘(UTC) 이미 트리거된 적 있는지 확인한다."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM alert_triggers WHERE alert_id=? AND triggered_at >= ?",
            (alert_id, today_start),
        ).fetchone()
        return int(row["c"]) > 0
    finally:
        conn.close()


def create_alert_trigger(
    alert_id: int,
    user_id: str,
    item_id: str,
    item_name: str,
    target_price: int,
    actual_price: int,
    direction: str,
    triggered_at: str,
) -> int:
    """알람 트리거 레코드를 생성한다. 생성된 id를 반환."""
    conn = _connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO alert_triggers
                (alert_id, user_id, item_id, item_name, target_price, actual_price,
                 direction, triggered_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (alert_id, user_id, item_id, item_name, target_price, actual_price,
             direction, triggered_at),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def list_triggered_alerts(
    user_id: str,
    since: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[AlertTrigger]:
    """사용자의 트리거된 알람 목록을 반환한다."""
    clauses = ["user_id = ?"]
    params: list[object] = [user_id]
    if since:
        clauses.append("triggered_at > ?")
        params.append(since)
    if unread_only:
        clauses.append("read_at IS NULL")
    params.append(limit)

    where = f"WHERE {' AND '.join(clauses)}"
    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM alert_triggers {where} ORDER BY triggered_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [
            AlertTrigger(
                id=r["id"],
                alert_id=r["alert_id"],
                user_id=r["user_id"],
                item_id=r["item_id"],
                item_name=r["item_name"] or "",
                target_price=r["target_price"],
                actual_price=r["actual_price"],
                direction=r["direction"],
                triggered_at=r["triggered_at"],
                pushed_at=r["pushed_at"],
                read_at=r["read_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def mark_trigger_read(trigger_id: int, user_id: str) -> bool:
    """트리거를 읽음 처리한다."""
    conn = _connect()
    try:
        cur = conn.execute(
            "UPDATE alert_triggers SET read_at=? WHERE id=? AND user_id=?",
            (_now_iso(), trigger_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ─── 디바이스 관리 (FCM 토큰) ─────────────────────────────────────────────────


def register_device(user_id: str, fcm_token: str, device_name: str = "", platform: str = "") -> int:
    """디바이스 FCM 토큰을 등록/갱신한다."""
    now = _now_iso()
    conn = _connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO user_devices (user_id, fcm_token, device_name, platform, created_at, updated_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(user_id, fcm_token) DO UPDATE SET
                device_name=excluded.device_name,
                platform=excluded.platform,
                updated_at=excluded.updated_at
            """,
            (user_id, fcm_token, device_name, platform, now, now),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def remove_device(user_id: str, fcm_token: str) -> bool:
    """디바이스 FCM 토큰을 제거한다."""
    conn = _connect()
    try:
        cur = conn.execute(
            "DELETE FROM user_devices WHERE user_id=? AND fcm_token=?",
            (user_id, fcm_token),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_user_device_tokens(user_id: str) -> list[str]:
    """사용자의 모든 FCM 토큰을 반환한다."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT fcm_token FROM user_devices WHERE user_id=?", (user_id,)
        ).fetchall()
        return [r["fcm_token"] for r in rows]
    finally:
        conn.close()


# ─── 사용자 관리 ──────────────────────────────────────────────────────────────


def upsert_user(
    google_id: str,
    email: str,
    name: str = "",
    profile_image: str = "",
) -> User:
    """Google 사용자를 생성하거나 마지막 로그인 시각을 갱신한다."""
    now = _now_iso()
    conn = _connect()
    try:
        # 기존 사용자 확인
        row = conn.execute(
            "SELECT * FROM users WHERE google_id=?", (google_id,)
        ).fetchone()

        if row:
            # 기존 사용자: last_login 갱신
            conn.execute(
                "UPDATE users SET last_login_at=?, name=?, profile_image=? WHERE google_id=?",
                (now, name or row["name"], profile_image or row["profile_image"], google_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM users WHERE google_id=?", (google_id,)
            ).fetchone()
        else:
            # 신규 사용자 생성
            conn.execute(
                """
                INSERT INTO users (google_id, email, name, profile_image, role, is_active, created_at, last_login_at)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (google_id, email, name, profile_image, "user", 1, now, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM users WHERE google_id=?", (google_id,)
            ).fetchone()

        return _row_to_user(row)
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> User | None:
    """사용자 ID로 조회한다."""
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return _row_to_user(row) if row else None
    finally:
        conn.close()


def list_users(limit: int = 100, offset: int = 0) -> list[User]:
    """전체 사용자 목록을 반환한다."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [_row_to_user(r) for r in rows]
    finally:
        conn.close()


def count_users() -> int:
    conn = _connect()
    try:
        return int(conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"])
    finally:
        conn.close()


def toggle_user_active(user_id: int) -> bool:
    """사용자 활성/비활성 토글. 성공 시 True."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE users SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",
            (user_id,),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def change_user_role(user_id: int, role: str) -> bool:
    """사용자 역할을 변경한다."""
    if role not in ("user", "admin"):
        return False
    conn = _connect()
    try:
        cur = conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _row_to_user(r: sqlite3.Row) -> User:
    return User(
        id=r["id"],
        google_id=r["google_id"],
        email=r["email"],
        name=r["name"] or "",
        profile_image=r["profile_image"] or "",
        role=r["role"],
        is_active=bool(r["is_active"]),
        created_at=r["created_at"],
        last_login_at=r["last_login_at"],
    )


# ─── 아이템 카탈로그 ──────────────────────────────────────────────────────────


def upsert_catalog_items(items: list[dict]) -> int:
    """카탈로그 아이템을 upsert한다. 저장된 건수를 반환."""
    if not items:
        return 0
    now = _now_iso()
    conn = _connect()
    try:
        cur = conn.cursor()
        for item in items:
            cur.execute(
                """
                INSERT INTO item_catalog
                    (source, item_code, item_name, kind_code, kind_name, rank_code, rank_name,
                     category_code, category_name, unit, canonical_id, latest_price,
                     price_change_rate, price_direction, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source, item_code, kind_code, rank_code) DO UPDATE SET
                    item_name=excluded.item_name,
                    kind_name=excluded.kind_name,
                    rank_name=excluded.rank_name,
                    category_name=excluded.category_name,
                    unit=excluded.unit,
                    canonical_id=excluded.canonical_id,
                    latest_price=excluded.latest_price,
                    price_change_rate=excluded.price_change_rate,
                    price_direction=excluded.price_direction,
                    updated_at=excluded.updated_at
                """,
                (
                    item.get("source", "KAMIS"),
                    item.get("item_code", ""),
                    item.get("item_name", ""),
                    item.get("kind_code", ""),
                    item.get("kind_name", ""),
                    item.get("rank_code", ""),
                    item.get("rank_name", ""),
                    item.get("category_code", ""),
                    item.get("category_name", ""),
                    item.get("unit", ""),
                    item.get("canonical_id", ""),
                    item.get("latest_price", 0),
                    item.get("price_change_rate", 0.0),
                    item.get("price_direction", ""),
                    now,
                ),
            )
        conn.commit()
        return len(items)
    finally:
        conn.close()


def query_catalog(
    category_code: str | None = None,
    search: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[CatalogItem]:
    """카탈로그 아이템을 조회한다."""
    clauses: list[str] = []
    params: list[object] = []
    if category_code:
        clauses.append("category_code = ?")
        params.append(category_code)
    if search:
        clauses.append("item_name LIKE ?")
        params.append(f"%{search}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([limit, offset])

    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM item_catalog {where} ORDER BY category_code, item_name LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [_row_to_catalog(r) for r in rows]
    finally:
        conn.close()


def count_catalog() -> int:
    conn = _connect()
    try:
        return int(conn.execute("SELECT COUNT(*) AS c FROM item_catalog").fetchone()["c"])
    finally:
        conn.close()


def _row_to_catalog(r: sqlite3.Row) -> CatalogItem:
    return CatalogItem(
        id=r["id"],
        source=r["source"],
        item_code=r["item_code"],
        item_name=r["item_name"],
        kind_code=r["kind_code"] or "",
        kind_name=r["kind_name"] or "",
        rank_code=r["rank_code"] or "",
        rank_name=r["rank_name"] or "",
        category_code=r["category_code"],
        category_name=r["category_name"] or "",
        unit=r["unit"] or "",
        canonical_id=r["canonical_id"],
        latest_price=r["latest_price"] or 0,
        price_change_rate=r["price_change_rate"] or 0.0,
        price_direction=r["price_direction"] or "",
        updated_at=r["updated_at"],
    )


# ─── 활동 로그 ────────────────────────────────────────────────────────────────


def log_activity(
    user_id: str = "",
    action: str = "",
    detail: str = "",
    ip_address: str = "",
    user_agent: str = "",
    user_email: str = "",
) -> None:
    """활동 로그를 기록한다."""
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO activity_logs (user_id, user_email, action, detail, ip_address, user_agent, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (user_id, user_email, action, detail[:500], ip_address, user_agent[:200], _now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def query_activity_logs(
    user_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ActivityLog]:
    """활동 로그를 조회한다."""
    clauses: list[str] = []
    params: list[object] = []
    if user_id:
        clauses.append("user_id = ?")
        params.append(user_id)
    if action:
        clauses.append("action = ?")
        params.append(action)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([limit, offset])

    conn = _connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM activity_logs {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [
            ActivityLog(
                id=r["id"],
                user_id=r["user_id"] or "",
                user_email=r["user_email"] or "",
                action=r["action"],
                detail=r["detail"] or "",
                ip_address=r["ip_address"] or "",
                user_agent=r["user_agent"] or "",
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def count_activity_logs() -> int:
    conn = _connect()
    try:
        return int(conn.execute("SELECT COUNT(*) AS c FROM activity_logs").fetchone()["c"])
    finally:
        conn.close()


def cleanup_activity_logs(cutoff_iso: str) -> int:
    """지정 시각 이전의 활동 로그를 삭제한다."""
    conn = _connect()
    try:
        cur = conn.execute(
            "DELETE FROM activity_logs WHERE created_at < ?", (cutoff_iso,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ─── DB 관리 ──────────────────────────────────────────────────────────────────


def get_table_stats() -> dict[str, int]:
    """각 테이블의 레코드 수를 반환한다."""
    tables = [
        "price_records", "collection_logs", "price_alerts", "alert_triggers",
        "user_devices", "users", "item_catalog", "activity_logs",
    ]
    conn = _connect()
    try:
        stats = {}
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
                stats[table] = int(row["c"])
            except sqlite3.OperationalError:
                stats[table] = 0
        return stats
    finally:
        conn.close()


def get_db_size() -> int:
    """DB 파일 크기(bytes)를 반환한다."""
    path = settings.cache_db_abspath
    return path.stat().st_size if path.exists() else 0
