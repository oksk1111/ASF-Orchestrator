const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const FA = `${API_BASE}/api/v1/fresh-alert`;

export interface RecommendationItem {
  item_id: string;
  item_name: string;
  category: string;
  avg_price: number;
  unit: string;
  sale_date: string;
  market_name: string;
  source: string;
}

export interface DailyRecommendation {
  date: string;
  recommendations: RecommendationItem[];
}

export interface KeywordItem {
  keyword: string;
  alert_enabled: boolean;
  threshold_pct: number;
}

export interface Notification {
  id: string;
  item_name: string;
  category: string;
  message: string;
  avg_price: number;
  change_pct: number;
  sale_date: string;
  market_name: string;
  read: boolean;
}

export interface SeasonItem {
  item_name: string;
  season: string;
  avg_price: number;
  in_cache: boolean;
}

export interface SeasonInfo {
  season: string;
  items: SeasonItem[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status}`);
  const json = await res.json();
  return json.data ?? json;
}

export const fetchRecommendations = (): Promise<DailyRecommendation> =>
  get(`${FA}/recommendations/today`);

export const fetchKeywords = (userId = "user_dev_01"): Promise<KeywordItem[]> =>
  get<{ user_id: string; keywords: KeywordItem[] }>(`${FA}/keywords?user_id=${userId}`)
    .then((res) => res.keywords);

export const fetchNotifications = (userId = "user_dev_01"): Promise<Notification[]> =>
  get<{ user_id: string; total: number; notifications: Notification[] }>(`${FA}/notifications?user_id=${userId}&limit=20`)
    .then((res) => res.notifications);

export const fetchCurrentSeason = (): Promise<SeasonInfo> =>
  get(`${FA}/seasons/current`);
