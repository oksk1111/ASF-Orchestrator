import type {
  CategoryInfo,
  CategorySubscription,
  CreateKeywordPayload,
  DailyRecommendation,
  FreshAlertResponse,
  Item,
  KeywordSubscription,
  MarketComparisonItem,
  Notification,
  PriceRecord,
  SeasonCalendarEntry,
  SeasonInfo,
  SubscribeCategoryPayload,
} from "../types/freshAlert"

const BASE_URL =
  process.env.EXPO_PUBLIC_FRESH_ALERT_API ?? "http://localhost:8000/api/v1/fresh-alert"

async function request<T>(path: string, options?: RequestInit): Promise<FreshAlertResponse<T>> {
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {}),
      },
      ...options,
    })

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`)
    }

    const json: FreshAlertResponse<T> = await res.json()
    return json
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error"
    return {
      status: "success",
      data: undefined as unknown as T,
      error: message,
    } as unknown as FreshAlertResponse<T>
  }
}

// Recommendations
export async function getRecommendations() {
  return request<DailyRecommendation>("/recommendations")
}

// Search
export async function searchItems(q: string) {
  return request<Item[]>(`/items/search?q=${encodeURIComponent(q)}`)
}

// Item detail
export async function getItemDetail(id: string) {
  return request<Item>(`/items/${id}`)
}

// Item prices
export async function getItemPrices(id: string, days: number = 30) {
  return request<PriceRecord[]>(`/items/${id}/prices?days=${days}`)
}

// Keywords
export async function getKeywords(userId: string) {
  return request<KeywordSubscription[]>(`/keywords?user_id=${userId}`)
}

export async function createKeyword(payload: CreateKeywordPayload) {
  return request<KeywordSubscription>("/keywords", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function deleteKeyword(id: string) {
  return request<{ deleted: boolean }>(`/keywords/${id}`, {
    method: "DELETE",
  })
}

// Categories
export async function getCategories() {
  return request<CategoryInfo[]>("/categories")
}

export async function subscribedCategories(userId: string) {
  return request<CategorySubscription[]>(`/categories/subscriptions?user_id=${userId}`)
}

export async function subscribeCategory(payload: SubscribeCategoryPayload) {
  return request<CategorySubscription>("/categories/subscriptions", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

// Notifications
export async function getNotifications(userId: string) {
  return request<Notification[]>(`/notifications?user_id=${userId}`)
}

// Season
export async function getCurrentSeason() {
  return request<SeasonInfo>("/season/current")
}

export async function getSeasonCalendar() {
  return request<SeasonCalendarEntry[]>("/season/calendar")
}

// Market comparison
export async function getMarketComparison(itemId: string) {
  return request<MarketComparisonItem[]>(`/items/${itemId}/markets`)
}
