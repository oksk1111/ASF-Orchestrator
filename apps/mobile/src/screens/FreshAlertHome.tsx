import { useCallback, useEffect, useState } from "react"
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native"

import { getKeywords, getRecommendations, subscribedCategories } from "../api/freshAlert"
import type {
  CategorySubscription,
  KeywordSubscription,
  RecommendationItem,
} from "../types/freshAlert"

const USER_ID = "user_dev_01"

export default function FreshAlertHome() {
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([])
  const [keywords, setKeywords] = useState<KeywordSubscription[]>([])
  const [categories, setCategories] = useState<CategorySubscription[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const [recRes, kwRes, catRes] = await Promise.all([
        getRecommendations(),
        getKeywords(USER_ID),
        subscribedCategories(USER_ID),
      ])

      if (recRes.data?.items) {
        setRecommendations(recRes.data.items.slice(0, 5))
      }
      if (kwRes.data) {
        setKeywords(kwRes.data)
      }
      if (catRes.data) {
        setCategories(catRes.data)
      }
    } catch {
      // silently handle - data stays as default
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    void fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={styles.accent.color} />
        <Text style={styles.loadingText}>오늘의 추천을 불러오는 중...</Text>
      </View>
    )
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#2E7D32" />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>FreshAlert</Text>
        <Text style={styles.headerSubtitle}>오늘의 신선식품 알리미</Text>
      </View>

      {/* Today's TOP 5 Recommendations */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>오늘의 추천 TOP 5</Text>
        {recommendations.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyText}>추천 데이터가 없습니다</Text>
          </View>
        ) : (
          recommendations.map((item) => (
            <View key={item.item_id} style={styles.recommendCard}>
              <View style={styles.rankBadge}>
                <Text style={styles.rankText}>{item.rank}</Text>
              </View>
              <View style={styles.recommendInfo}>
                <Text style={styles.itemName}>{item.item_name}</Text>
                <Text style={styles.itemCategory}>{item.large_name}</Text>
              </View>
              <View style={styles.recommendRight}>
                <Text style={styles.priceDropText}>
                  ▼ {item.price_drop_rate.toFixed(1)}%
                </Text>
                {item.is_season && (
                  <View style={styles.seasonBadge}>
                    <Text style={styles.seasonBadgeText}>제철</Text>
                  </View>
                )}
              </View>
            </View>
          ))
        )}
      </View>

      {/* My Keywords Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>내 키워드</Text>
        {keywords.length === 0 ? (
          <Text style={styles.emptyText}>등록된 키워드가 없습니다</Text>
        ) : (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.chipRow}
          >
            {keywords.map((kw) => (
              <TouchableOpacity
                key={kw.id}
                style={[styles.chip, !kw.enabled && styles.chipDisabled]}
              >
                <Text style={[styles.chipText, !kw.enabled && styles.chipTextDisabled]}>
                  {kw.item_name}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}
      </View>

      {/* My Categories Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>내 카테고리</Text>
        {categories.length === 0 ? (
          <Text style={styles.emptyText}>구독 중인 카테고리가 없습니다</Text>
        ) : (
          <View style={styles.categoryGrid}>
            {categories.map((cat) => (
              <View key={cat.id} style={styles.categoryCard}>
                <Text style={styles.categoryName}>{cat.large_name}</Text>
                {cat.mid_name && (
                  <Text style={styles.categoryMid}>{cat.mid_name}</Text>
                )}
                <Text style={styles.categoryDays}>
                  {cat.notify_days.join(", ")}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#FAFAFA",
  },
  content: {
    paddingBottom: 32,
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#FAFAFA",
  },
  accent: {
    color: "#2E7D32",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: "#666",
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 16,
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: "#E8E8E8",
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: "700",
    color: "#2E7D32",
  },
  headerSubtitle: {
    fontSize: 14,
    color: "#666",
    marginTop: 4,
  },
  section: {
    marginTop: 20,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1A1A1A",
    marginBottom: 12,
  },
  emptyCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 24,
    alignItems: "center",
  },
  emptyText: {
    fontSize: 14,
    color: "#999",
  },
  recommendCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  rankBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#2E7D32",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
  },
  rankText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
  },
  recommendInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 16,
    fontWeight: "500",
    color: "#1A1A1A",
  },
  itemCategory: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  recommendRight: {
    alignItems: "flex-end",
  },
  priceDropText: {
    fontSize: 15,
    fontWeight: "600",
    color: "#D32F2F",
  },
  seasonBadge: {
    marginTop: 4,
    backgroundColor: "#E8F5E9",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  seasonBadgeText: {
    fontSize: 11,
    fontWeight: "600",
    color: "#2E7D32",
  },
  chipRow: {
    flexDirection: "row",
    gap: 8,
    paddingVertical: 4,
  },
  chip: {
    backgroundColor: "#E8F5E9",
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#2E7D32",
  },
  chipDisabled: {
    backgroundColor: "#F5F5F5",
    borderColor: "#CCC",
  },
  chipText: {
    fontSize: 13,
    fontWeight: "500",
    color: "#2E7D32",
  },
  chipTextDisabled: {
    color: "#999",
  },
  categoryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  categoryCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 16,
    width: "48%",
    borderLeftWidth: 3,
    borderLeftColor: "#2E7D32",
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  categoryName: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1A1A1A",
  },
  categoryMid: {
    fontSize: 12,
    color: "#666",
    marginTop: 2,
  },
  categoryDays: {
    fontSize: 11,
    color: "#999",
    marginTop: 6,
  },
})
