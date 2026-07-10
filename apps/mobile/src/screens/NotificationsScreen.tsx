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

import { getNotifications } from "../api/freshAlert"
import type { Notification } from "../types/freshAlert"

const USER_ID = "user_dev_01"

type NotificationType = "recommend" | "keyword" | "category"

const TYPE_LABELS: Record<NotificationType, string> = {
  recommend: "추천 알림",
  keyword: "키워드 알림",
  category: "카테고리 알림",
}

const TYPE_COLORS: Record<NotificationType, string> = {
  recommend: "#2E7D32",
  keyword: "#1565C0",
  category: "#E65100",
}

export default function NotificationsScreen() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await getNotifications(USER_ID)
      if (res.data) {
        setNotifications(res.data)
      }
    } catch {
      // handle silently
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void fetchNotifications()
  }, [fetchNotifications])

  const onRefresh = useCallback(() => {
    setRefreshing(true)
    void fetchNotifications()
  }, [fetchNotifications])

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, read_at: new Date().toISOString() } : n
      )
    )
    // In production, call API to persist read state
  }

  const formatTime = (dateStr: string): string => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    const diffHour = Math.floor(diffMin / 60)
    const diffDay = Math.floor(diffHour / 24)

    if (diffMin < 1) return "방금 전"
    if (diffMin < 60) return `${diffMin}분 전`
    if (diffHour < 24) return `${diffHour}시간 전`
    if (diffDay < 7) return `${diffDay}일 전`
    return date.toLocaleDateString("ko-KR")
  }

  // Group notifications by type
  const grouped = notifications.reduce<Record<NotificationType, Notification[]>>(
    (acc, n) => {
      acc[n.type].push(n)
      return acc
    },
    { recommend: [], keyword: [], category: [] }
  )

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2E7D32" />
      </View>
    )
  }

  const typeOrder: NotificationType[] = ["recommend", "keyword", "category"]

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
        <Text style={styles.headerTitle}>알림</Text>
        <Text style={styles.headerCount}>
          읽지 않음 {notifications.filter((n) => !n.read_at).length}건
        </Text>
      </View>

      {notifications.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>알림이 없습니다</Text>
        </View>
      ) : (
        typeOrder.map((type) => {
          const items = grouped[type]
          if (items.length === 0) return null

          return (
            <View key={type} style={styles.group}>
              <View style={styles.groupHeader}>
                <View
                  style={[
                    styles.groupDot,
                    { backgroundColor: TYPE_COLORS[type] },
                  ]}
                />
                <Text style={styles.groupTitle}>{TYPE_LABELS[type]}</Text>
                <Text style={styles.groupCount}>{items.length}</Text>
              </View>

              {items.map((notification) => {
                const isUnread = !notification.read_at
                return (
                  <TouchableOpacity
                    key={notification.id}
                    style={[
                      styles.notificationCard,
                      isUnread && styles.notificationCardUnread,
                    ]}
                    onPress={() => markAsRead(notification.id)}
                    activeOpacity={0.7}
                  >
                    <View style={styles.notificationContent}>
                      <View style={styles.notificationTop}>
                        <Text
                          style={[
                            styles.notificationTitle,
                            isUnread && styles.notificationTitleUnread,
                          ]}
                          numberOfLines={1}
                        >
                          {notification.title}
                        </Text>
                        {isUnread && <View style={styles.unreadDot} />}
                      </View>
                      <Text style={styles.notificationBody} numberOfLines={2}>
                        {notification.body}
                      </Text>
                      <Text style={styles.notificationTime}>
                        {formatTime(notification.sent_at)}
                      </Text>
                    </View>
                  </TouchableOpacity>
                )
              })}
            </View>
          )
        })
      )}
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
  header: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#E8E8E8",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1A1A1A",
  },
  headerCount: {
    fontSize: 13,
    color: "#2E7D32",
    fontWeight: "500",
  },
  emptyContainer: {
    paddingVertical: 60,
    alignItems: "center",
  },
  emptyText: {
    fontSize: 14,
    color: "#999",
  },
  group: {
    marginTop: 20,
    paddingHorizontal: 20,
  },
  groupHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
  },
  groupDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  groupTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1A1A1A",
  },
  groupCount: {
    fontSize: 13,
    color: "#888",
    marginLeft: 8,
  },
  notificationCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    shadowColor: "#000",
    shadowOpacity: 0.03,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  notificationCardUnread: {
    borderLeftWidth: 3,
    borderLeftColor: "#2E7D32",
  },
  notificationContent: {
    flex: 1,
  },
  notificationTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  notificationTitle: {
    fontSize: 15,
    fontWeight: "400",
    color: "#1A1A1A",
    flex: 1,
  },
  notificationTitleUnread: {
    fontWeight: "600",
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#2E7D32",
    marginLeft: 8,
  },
  notificationBody: {
    fontSize: 13,
    color: "#666",
    marginTop: 6,
    lineHeight: 18,
  },
  notificationTime: {
    fontSize: 11,
    color: "#AAA",
    marginTop: 8,
  },
})
