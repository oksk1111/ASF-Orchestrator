import { useEffect, useState } from "react";
import {
  DailyRecommendation,
  KeywordItem,
  Notification,
  SeasonInfo,
  fetchCurrentSeason,
  fetchKeywords,
  fetchNotifications,
  fetchRecommendations,
} from "../api/freshAlert";

// ─── 추천 TOP5 ────────────────────────────────────────────────────────────────

function RecommendSection() {
  const [data, setData] = useState<DailyRecommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchRecommendations()
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <article className="module-card">
      <div className="fa-card-header">
        <h2>오늘의 추천 TOP 5</h2>
        {data && <span className="fa-date">{data.date}</span>}
      </div>

      {loading && <p className="fa-loading">분석 중...</p>}
      {error && <p className="fa-error">백엔드 API 연결 필요</p>}

      {data && (
        <ul className="fa-rec-list">
          {data.recommendations.map((item, idx) => (
            <li key={item.item_id} className="fa-rec-row">
              <span className="fa-rank">{idx + 1}</span>
              <div className="fa-rec-info">
                <strong>{item.item_name}</strong>
                <small>{item.category}</small>
              </div>
              <div className="fa-rec-right">
                <span className="fa-drop">{item.avg_price.toLocaleString()}원</span>
                <span className="fa-season-badge">{item.market_name}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

// ─── 제철 캘린더 ──────────────────────────────────────────────────────────────

function SeasonSection() {
  const [data, setData] = useState<SeasonInfo | null>(null);

  useEffect(() => {
    fetchCurrentSeason().then(setData).catch(() => null);
  }, []);

  const monthNames = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];

  return (
    <article className="module-card">
      <div className="fa-card-header">
        <h2>이달의 제철</h2>
        {data && <span className="fa-date">{data.season}</span>}
      </div>

      {!data && <p className="fa-loading">불러오는 중...</p>}

      {data && (
        <div className="fa-season-grid">
          <div className="fa-season-group">
            <span className="fa-season-label">🌿 이달의 제철</span>
            <div className="fa-chips">
              {data.items.map((item) => (
                <span key={item.item_name} className="fa-chip">{item.item_name}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

// ─── 키워드 구독 ──────────────────────────────────────────────────────────────

function KeywordSection() {
  const [data, setData] = useState<KeywordItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchKeywords()
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <article className="module-card">
      <div className="fa-card-header">
        <h2>내 키워드 알림</h2>
        <span className="fa-date">{data.length}/20</span>
      </div>

      {loading && <p className="fa-loading">불러오는 중...</p>}

      {!loading && data.length === 0 && (
        <p className="fa-empty">등록된 키워드가 없습니다</p>
      )}

      {data.length > 0 && (
        <div className="fa-keyword-list">
          {data.map((kw) => (
            <div key={kw.keyword} className={`fa-keyword-chip${kw.alert_enabled ? "" : " disabled"}`}>
              <span>{kw.keyword}</span>
              <small>{kw.threshold_pct}% 이상 변동 시</small>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

// ─── 알림 목록 ────────────────────────────────────────────────────────────────

const TYPE_LABEL: Record<string, string> = {
  recommend: "추천",
  keyword: "키워드",
  category: "카테고리",
};

const TYPE_COLOR: Record<string, string> = {
  recommend: "#2c4f3e",
  keyword: "#1565c0",
  category: "#e65100",
};

function formatRelTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "방금 전";
  if (m < 60) return `${m}분 전`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
}

function NotificationSection() {
  const [data, setData] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNotifications()
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, []);

  const unread = data.filter((n) => !n.read).length;

  return (
    <article className="module-card wide">
      <div className="fa-card-header">
        <h2>최근 알림</h2>
        {unread > 0 && <span className="fa-unread-badge">{unread}개 읽지 않음</span>}
      </div>

      {loading && <p className="fa-loading">불러오는 중...</p>}

      {!loading && data.length === 0 && (
        <p className="fa-empty">알림이 없습니다</p>
      )}

      {data.length > 0 && (
        <ul className="fa-notif-list">
          {data.map((n, idx) => (
            <li key={`${n.id}-${idx}`} className={`fa-notif-row${n.read ? "" : " unread"}`}>
              <span className="fa-notif-type" style={{ background: "#2c4f3e18", color: "#2c4f3e" }}>
                {n.category}
              </span>
              <div className="fa-notif-body">
                <strong>{n.item_name}</strong>
                <p>{n.message}</p>
              </div>
              <span className="fa-notif-time">
                {n.sale_date.slice(0,4)}.{n.sale_date.slice(4,6)}.{n.sale_date.slice(6,8)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

// ─── 메인 FreshAlert 섹션 ─────────────────────────────────────────────────────

export default function FreshAlertSection() {
  return (
    <section className="fresh-alert-section" id="fresh-alert">
      <div className="fa-section-header">
        <div>
          <h2>FreshAlert</h2>
          <p>실시간 제철 농식품 가격 알림 서비스 — 오늘 가장 저렴한 신선식품을 확인하세요</p>
        </div>
        <span className="fa-live-badge">● LIVE</span>
      </div>

      <div className="module-grid">
        <RecommendSection />
        <SeasonSection />
        <KeywordSection />
        <NotificationSection />
      </div>
    </section>
  );
}
