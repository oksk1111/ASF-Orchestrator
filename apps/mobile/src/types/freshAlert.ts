export interface Item {
  item_id: string
  large_code: string
  mid_code: string
  small_code: string
  large_name: string
  mid_name: string
  small_name: string
  season_start: number | null
  season_end: number | null
}

export interface PriceRecord {
  item_id: string
  market_code: string
  market_name: string
  sale_date: string
  avg_price: number
  min_price: number
  max_price: number
  total_qty: number
  total_amt: number
  data_source: "MAFRA" | "KAMIS"
}

export interface RecommendationItem {
  rank: number
  item_id: string
  item_name: string
  large_name: string
  current_price: number
  avg_30d: number
  price_drop_rate: number
  is_season: boolean
  recommend_score: number
}

export interface DailyRecommendation {
  date: string
  items: RecommendationItem[]
}

export interface KeywordSubscription {
  id: string
  user_id: string
  item_id: string
  item_name: string
  threshold_type: "percentage" | "absolute"
  threshold_value: number
  enabled: boolean
}

export interface CategorySubscription {
  id: string
  user_id: string
  large_code: string
  large_name: string
  mid_code: string | null
  mid_name: string | null
  notify_days: string[]
  enabled: boolean
}

export interface Notification {
  id: string
  user_id: string
  type: "recommend" | "keyword" | "category"
  title: string
  body: string
  item_id: string | null
  sent_at: string
  read_at: string | null
}

export interface SeasonCalendarEntry {
  month: number
  vegetables: string[]
  fruits: string[]
  seafood: string[]
}

export interface MarketComparisonItem {
  market_code: string
  market_name: string
  avg_price: number
  price_drop_rate: number
}

export interface FreshAlertResponse<T> {
  status: "success"
  data: T
}

export interface CategoryInfo {
  large_code: string
  large_name: string
  mid_categories: { code: string; name: string }[]
}

export interface DailyAnalysis {
  item_id: string
  date: string
  avg_price: number
  min_price: number
  max_price: number
  price_change: number
  price_change_percent: number
  volatility: number
}

export interface CreateKeywordPayload {
  user_id: string
  item_id: string
  item_name: string
  threshold_type: "percentage" | "absolute"
  threshold_value: number
}

export interface SubscribeCategoryPayload {
  user_id: string
  large_code: string
  large_name: string
  mid_code?: string
  mid_name?: string
  notify_days: string[]
}

export interface SeasonInfo {
  current_season: string
  month: number
  featured_items: string[]
}
