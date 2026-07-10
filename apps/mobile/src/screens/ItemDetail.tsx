import { useCallback, useEffect, useState } from "react"
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native"

import {
  getItemDetail,
  getItemPrices,
  getMarketComparison,
} from "../api/freshAlert"
import type { Item, MarketComparisonItem, PriceRecord } from "../types/freshAlert"

interface ItemDetailProps {
  itemId: string
  onKeywordRegister?: (item: Item) => void
  onBookmark?: (item: Item) => void
}

export default function ItemDetail({ itemId, onKeywordRegister, onBookmark }: ItemDetailProps) {
  const [item, setItem] = useState<Item | null>(null)
  const [prices, setPrices] = useState<PriceRecord[]>([])
  const [markets, setMarkets] = useState<MarketComparisonItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [itemRes, priceRes, marketRes] = await Promise.all([
        getItemDetail(itemId),
        getItemPrices(itemId, 30),
        getMarketComparison(itemId),
      ])

      if (itemRes.data) setItem(itemRes.data)
      if (priceRes.data) setPrices(priceRes.data)
      if (marketRes.data) setMarkets(marketRes.data)
    } catch {
      // handle silently
    } finally {
      setLoading(false)
    }
  }, [itemId])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2E7D32" />
      </View>
    )
  }

  if (!item) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>품목 정보를 불러올 수 없습니다</Text>
      </View>
    )
  }

  // Calculate stats
  const recentPrices = prices.slice(-7)
  const allPriceValues = prices.map((p) => p.avg_price)
  const currentPrice = allPriceValues.length > 0 ? allPriceValues[allPriceValues.length - 1] : 0
  const avg30d =
    allPriceValues.length > 0
      ? allPriceValues.reduce((a, b) => a + b, 0) / allPriceValues.length
      : 0
  const priceDiffPercent = avg30d > 0 ? ((currentPrice - avg30d) / avg30d) * 100 : 0

  // Season info
  const currentMonth = new Date().getMonth() + 1
  const isInSeason =
    item.season_start !== null &&
    item.season_end !== null &&
    currentMonth >= item.season_start &&
    currentMonth <= item.season_end

  // Simple text-based price trend for last 7 data points
  const renderPriceTrend = () => {
    if (recentPrices.length === 0) {
      return <Text style={styles.noDataText}>가격 데이터가 없습니다</Text>
    }

    const maxP = Math.max(...recentPrices.map((p) => p.avg_price))
    const minP = Math.min(...recentPrices.map((p) => p.avg_price))
    const range = maxP - minP || 1

    return (
      <View style={styles.trendContainer}>
        {recentPrices.map((record, idx) => {
          const barWidth = ((record.avg_price - minP) / range) * 100
          const dateLabel = record.sale_date.slice(5) // MM-DD
          return (
            <View key={`${record.sale_date}-${idx}`} style={styles.trendRow}>
              <Text style={styles.trendDate}>{dateLabel}</Text>
              <View style={styles.trendBarBg}>
                <View
                  style={[
                    styles.trendBar,
                    { width: `${Math.max(barWidth, 10)}%` },
                  ]}
                />
              </View>
              <Text style={styles.trendPrice}>
                {record.avg_price.toLocaleString()}원
              </Text>
            </View>
          )
        })}
      </View>
    )
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Item Header */}
      <View style={styles.itemHeader}>
        <View style={styles.itemTitleRow}>
          <Text style={styles.itemName}>{item.small_name}</Text>
          {isInSeason && (
            <View style={styles.seasonBadge}>
              <Text style={styles.seasonBadgeText}>제철</Text>
            </View>
          )}
        </View>
        <Text style={styles.itemCategory}>
          {item.large_name} &gt; {item.mid_name}
        </Text>
        {item.season_start && item.season_end && (
          <Text style={styles.seasonInfo}>
            제철: {item.season_start}월 ~ {item.season_end}월
          </Text>
        )}
      </View>

      {/* Price Summary */}
      <View style={styles.priceCard}>
        <Text style={styles.priceCardTitle}>가격 현황</Text>
        <View style={styles.priceRow}>
          <View style={styles.priceCol}>
            <Text style={styles.priceLabel}>현재가</Text>
            <Text style={styles.priceValue}>
              {currentPrice.toLocaleString()}원
            </Text>
          </View>
          <View style={styles.priceDivider} />
          <View style={styles.priceCol}>
            <Text style={styles.priceLabel}>30일 평균</Text>
            <Text style={styles.priceValue}>
              {Math.round(avg30d).toLocaleString()}원
            </Text>
          </View>
          <View style={styles.priceDivider} />
          <View style={styles.priceCol}>
            <Text style={styles.priceLabel}>차이</Text>
            <Text
              style={[
                styles.priceValue,
                priceDiffPercent < 0 ? styles.priceDown : styles.priceUp,
              ]}
            >
              {priceDiffPercent > 0 ? "+" : ""}
              {priceDiffPercent.toFixed(1)}%
            </Text>
          </View>
        </View>
      </View>

      {/* Price Trend (text-based) */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>최근 7일 가격 추이</Text>
        {renderPriceTrend()}
      </View>

      {/* Market Comparison */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>시장별 비교</Text>
        {markets.length === 0 ? (
          <Text style={styles.noDataText}>비교 데이터가 없습니다</Text>
        ) : (
          markets.map((m, idx) => (
            <View
              key={`${m.market_code}-${idx}`}
              style={[
                styles.marketRow,
                idx === 0 && styles.marketRowFirst,
              ]}
            >
              <View style={styles.marketInfo}>
                <Text style={styles.marketName}>{m.market_name}</Text>
                {m.price_drop_rate > 0 && (
                  <Text style={styles.marketDrop}>
                    ▼ {m.price_drop_rate.toFixed(1)}%
                  </Text>
                )}
              </View>
              <Text style={styles.marketPrice}>
                {m.avg_price.toLocaleString()}원
              </Text>
            </View>
          ))
        )}
      </View>

      {/* Action Buttons */}
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={() => onKeywordRegister?.(item)}
        >
          <Text style={styles.primaryButtonText}>키워드 등록</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={() => onBookmark?.(item)}
        >
          <Text style={styles.secondaryButtonText}>북마크</Text>
        </TouchableOpacity>
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
    paddingBottom: 40,
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#FAFAFA",
  },
  errorText: {
    fontSize: 14,
    color: "#999",
  },
  itemHeader: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 20,
    paddingVertical: 24,
    borderBottomWidth: 1,
    borderBottomColor: "#E8E8E8",
  },
  itemTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  itemName: {
    fontSize: 22,
    fontWeight: "700",
    color: "#1A1A1A",
  },
  seasonBadge: {
    backgroundColor: "#E8F5E9",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  seasonBadgeText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#2E7D32",
  },
  itemCategory: {
    fontSize: 14,
    color: "#666",
    marginTop: 6,
  },
  seasonInfo: {
    fontSize: 13,
    color: "#2E7D32",
    marginTop: 4,
  },
  priceCard: {
    backgroundColor: "#FFFFFF",
    marginHorizontal: 20,
    marginTop: 16,
    borderRadius: 12,
    padding: 20,
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  priceCardTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1A1A1A",
    marginBottom: 16,
  },
  priceRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  priceCol: {
    flex: 1,
    alignItems: "center",
  },
  priceDivider: {
    width: 1,
    height: 36,
    backgroundColor: "#E8E8E8",
  },
  priceLabel: {
    fontSize: 12,
    color: "#888",
    marginBottom: 4,
  },
  priceValue: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1A1A1A",
  },
  priceDown: {
    color: "#2E7D32",
  },
  priceUp: {
    color: "#D32F2F",
  },
  section: {
    marginTop: 20,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1A1A1A",
    marginBottom: 12,
  },
  noDataText: {
    fontSize: 13,
    color: "#999",
    textAlign: "center",
    paddingVertical: 12,
  },
  trendContainer: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 16,
  },
  trendRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  trendDate: {
    width: 48,
    fontSize: 12,
    color: "#666",
  },
  trendBarBg: {
    flex: 1,
    height: 16,
    backgroundColor: "#F0F0F0",
    borderRadius: 4,
    marginHorizontal: 8,
    overflow: "hidden",
  },
  trendBar: {
    height: 16,
    backgroundColor: "#66BB6A",
    borderRadius: 4,
  },
  trendPrice: {
    width: 72,
    fontSize: 12,
    color: "#1A1A1A",
    textAlign: "right",
  },
  marketRow: {
    backgroundColor: "#FFFFFF",
    borderRadius: 10,
    padding: 14,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  marketRowFirst: {
    borderWidth: 1,
    borderColor: "#2E7D32",
  },
  marketInfo: {
    flex: 1,
  },
  marketName: {
    fontSize: 14,
    fontWeight: "500",
    color: "#1A1A1A",
  },
  marketDrop: {
    fontSize: 12,
    color: "#2E7D32",
    marginTop: 2,
  },
  marketPrice: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1A1A1A",
  },
  actionRow: {
    flexDirection: "row",
    paddingHorizontal: 20,
    marginTop: 28,
    gap: 12,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: "#2E7D32",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
    borderWidth: 1.5,
    borderColor: "#2E7D32",
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#2E7D32",
  },
})
