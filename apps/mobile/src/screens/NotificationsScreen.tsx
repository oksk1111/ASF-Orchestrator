import React, { useEffect, useState, useCallback } from "react"
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from "react-native"
import { getNotifications, markNotificationRead } from "../api/freshAlert"
import { Notification } from "../types/freshAlert"

const TYPE_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  recommend: { emoji: "📢", label: "추천", color: "#2E7D32" },
  keyword: { emoji: "🔑", label: "키워드", color: "#1565C0" },
  category: { emoji: "📁", label: "카테고리", color: "#E65100" },
}

export default function NotificationsScreen() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadNotifications = useCallback(async () => {
    try {
      const data = await getNotifications("user_dev_01", 100)
      if (Array.isArray(data)) {
        setNotifications(data)
      }
    } catch (e) {
      console.error("Failed to load notifications:", e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadNotifications() }, [loadNotifications])

  const onRefresh = useCallback(async () => {
    setRefreshing(true)
    await loadNotifications()
    setRefreshing(false)
  }, [loadNotifications])

  const handleRead = async (notifId: string) => {
    try {
      await markNotificationRead(notifId, "user_dev_01")
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notifId ? { ...n, read_at: new Date().toISOString() } : n
        )
      )
    } catch (e) {
      console.error("Failed to mark read:", e)
    }
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}분 전`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}시간 전`
    const days = Math.floor(hours / 24)
    return `${days}일 전`
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2E7D32" />
      </View>
    )
  }

  const renderNotification = ({ item }: { item: Notification }) => {
    const config = TYPE_CONFIG[item.type] || TYPE_CONFIG.recommend
    const isUnread = !item.read_at

    return (
      <TouchableOpacity
        style={[styles.card, isUnread && styles.cardUnread]}
        onPress={() => isUnread && handleRead(item.id)}
      >
        <View style={styles.cardHeader}>
          <View style={[styles.typeBadge, { backgroundColor: config.color + "15" }]}>
            <Text style={styles.typeEmoji}>{config.emoji}</Text>
            <Text style={[styles.typeLabel, { color: config.color }]}>{config.label}</Text>
          </View>
          <Text style={styles.timeText}>{formatTime(item.sent_at)}</Text>
        </View>
        <Text style={[styles.cardTitle, isUnread && styles.cardTitleBold]}>{item.title}</Text>
        <Text style={styles.cardBody}>{item.body}</Text>
        {isUnread && <View style={styles.unreadDot} />}
      </TouchableOpacity>
    )
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🔔 알림</Text>
        <Text style={styles.headerCount}>
          {notifications.filter((n) => !n.read_at).length}개 읽지 않음
        </Text>
      </View>

      {notifications.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyEmoji}>🔕</Text>
          <Text style={styles.emptyText}>아직 알림이 없습니다</Text>
          <Text style={styles.emptySubtext}>
            키워드를 등록하거나 카테고리를 구독하면{"\n"}
            가격 변동 시 알림을 받을 수 있어요
          </Text>
        </View>
      ) : (
        <FlatList
          data={notifications}
          keyExtractor={(item) => item.id}
          renderItem={renderNotification}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={["#2E7D32"]} />
          }
          contentContainerStyle={styles.list}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAF8" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { paddingHorizontal: 20, paddingTop: 60, paddingBottom: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E8E8E8" },
  headerTitle: { fontSize: 22, fontWeight: "bold", color: "#212121" },
  headerCount: { fontSize: 13, color: "#888", marginTop: 4 },
  list: { padding: 16 },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, marginBottom: 10, position: "relative", elevation: 1, shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 4 },
  cardUnread: { borderLeftWidth: 3, borderLeftColor: "#2E7D32" },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  typeBadge: { flexDirection: "row", alignItems: "center", paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10 },
  typeEmoji: { fontSize: 12, marginRight: 4 },
  typeLabel: { fontSize: 12, fontWeight: "500" },
  timeText: { fontSize: 12, color: "#999" },
  cardTitle: { fontSize: 15, color: "#333", marginBottom: 4 },
  cardTitleBold: { fontWeight: "600", color: "#212121" },
  cardBody: { fontSize: 13, color: "#666", lineHeight: 18 },
  unreadDot: { position: "absolute", top: 16, right: 16, width: 8, height: 8, borderRadius: 4, backgroundColor: "#2E7D32" },
  empty: { flex: 1, justifyContent: "center", alignItems: "center", paddingHorizontal: 40 },
  emptyEmoji: { fontSize: 48, marginBottom: 16 },
  emptyText: { fontSize: 18, fontWeight: "600", color: "#333" },
  emptySubtext: { fontSize: 14, color: "#888", textAlign: "center", marginTop: 8, lineHeight: 20 },
})
