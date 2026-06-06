import { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { mobileTokens } from "./src/theme/tokens";

const API_BASE = "http://localhost:8000";

type BasketItem = {
  product_code: string;
  product_name: string;
  discounted_price: number;
  nutrition_match_reason: string;
  oversupply_risk_level: string;
};

export default function App() {
  const [basketItems, setBasketItems] = useState<BasketItem[]>([]);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [selectedSize, setSelectedSize] = useState<string | null>(null);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const tokenRes = await fetch(`${API_BASE}/api/v1/auth/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: "user_dev_01" }),
        });
        const tokenPayload = await tokenRes.json();

        const basketRes = await fetch(`${API_BASE}/api/v1/recommendation/basket`, {
          headers: {
            Authorization: `Bearer ${tokenPayload.access_token}`,
          },
        });
        const basketPayload = await basketRes.json();
        setBasketItems(basketPayload.data.items ?? []);
      } catch {
        setBasketItems([]);
      }
    };

    void bootstrap();
  }, []);

  const featuredItem = useMemo(() => basketItems[0], [basketItems]);

  const sizeRows = [
    { label: "S", urgency: "Only 2 Left" },
    { label: "M", urgency: "Selling Fast" },
    { label: "L", urgency: "Only 1 Left" },
    { label: "XL", urgency: "" },
  ];

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.navbar}>
        <Text style={styles.brand}>ASFMOBILE</Text>
        <View style={styles.navActions}>
          <Text style={styles.navAction}>Search</Text>
          <Text style={styles.navAction}>Menu</Text>
          <Text style={styles.navAction}>Bag: 0</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.productImageCard}>
          <Text style={styles.imagePlaceholder}>AI SMART BASKET</Text>
          <View style={styles.dotRow}>
            <View style={[styles.dot, styles.dotActive]} />
            <View style={styles.dot} />
            <View style={styles.dot} />
          </View>
        </View>

        <View style={styles.infoBar}>
          <View style={styles.infoRow}>
            <Text style={styles.productName}>{featuredItem?.product_name ?? "추천 품목 로딩 중"}</Text>
            <Text style={styles.price}>₩{Math.round(featuredItem?.discounted_price ?? 0)}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.subtitle}>{featuredItem?.nutrition_match_reason ?? "식단 매칭 분석"}</Text>
          </View>
          <View style={styles.infoRowBottom}>
            <TouchableOpacity style={styles.selectButton} onPress={() => setSheetOpen(true)}>
              <Text style={styles.selectButtonLabel}>
                {selectedSize ? `Size ${selectedSize}` : "Select Size"}
              </Text>
            </TouchableOpacity>
            <Text style={styles.utilityLink}>More Info</Text>
          </View>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity style={styles.addToBag}>
          <Text style={styles.addToBagLabel}>Add to Bag</Text>
        </TouchableOpacity>
        <Text style={styles.utilityLink}>US Size Guide &gt;</Text>
      </View>

      <Modal visible={sheetOpen} transparent animationType="slide" onRequestClose={() => setSheetOpen(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setSheetOpen(false)} />
        <View style={styles.sheet}>
          <View style={styles.sheetHeader}>
            <View style={styles.dragHandle} />
          </View>
          {sizeRows.map((row) => (
            <TouchableOpacity
              key={row.label}
              style={styles.sizeRow}
              onPress={() => {
                setSelectedSize(row.label);
                setSheetOpen(false);
              }}
            >
              <View
                style={[
                  styles.sizeCircle,
                  selectedSize === row.label ? styles.sizeCircleSelected : undefined,
                ]}
              >
                <Text
                  style={[
                    styles.sizeLabel,
                    selectedSize === row.label ? styles.sizeLabelSelected : undefined,
                  ]}
                >
                  {row.label}
                </Text>
              </View>
              <View style={styles.rowSpacer} />
              <Text style={styles.urgency}>{row.urgency}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: mobileTokens.colors.pageSurface,
  },
  navbar: {
    height: 56,
    paddingHorizontal: 24,
    backgroundColor: mobileTokens.colors.pureWhite,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brand: {
    fontSize: 22,
    fontWeight: "700",
    letterSpacing: 2.6,
    color: mobileTokens.colors.brandBlack,
  },
  navActions: {
    flexDirection: "row",
    gap: 20,
  },
  navAction: {
    fontSize: 14,
    color: mobileTokens.colors.brandBlack,
  },
  content: {
    paddingHorizontal: 24,
    paddingVertical: 18,
    gap: 16,
  },
  productImageCard: {
    borderRadius: mobileTokens.radius.productImageCard,
    backgroundColor: mobileTokens.colors.pageSurface,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 300,
    ...mobileTokens.shadow.card,
  },
  imagePlaceholder: {
    fontSize: 20,
    letterSpacing: 1.5,
    color: mobileTokens.colors.brandBlack,
  },
  dotRow: {
    position: "absolute",
    bottom: 16,
    flexDirection: "row",
    gap: 6,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#D1D5DB",
  },
  dotActive: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: mobileTokens.colors.brandBlack,
  },
  infoBar: {
    borderRadius: mobileTokens.radius.productInfoBar,
    backgroundColor: mobileTokens.colors.pureWhite,
    paddingHorizontal: 24,
    paddingVertical: 20,
    ...mobileTokens.shadow.card,
  },
  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  infoRowBottom: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 8,
  },
  productName: {
    fontSize: 17,
    color: mobileTokens.colors.brandBlack,
  },
  price: {
    fontSize: 17,
    color: mobileTokens.colors.brandBlack,
  },
  subtitle: {
    fontSize: 14,
    fontStyle: "italic",
    color: mobileTokens.colors.descriptionGray,
    flex: 1,
  },
  selectButton: {
    backgroundColor: mobileTokens.colors.brandBlack,
    borderRadius: 50,
    paddingHorizontal: 28,
    paddingVertical: 14,
    minWidth: 180,
    alignItems: "center",
  },
  selectButtonLabel: {
    fontSize: 15,
    fontWeight: "500",
    color: mobileTokens.colors.pureWhite,
  },
  footer: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: mobileTokens.colors.pureWhite,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  addToBag: {
    backgroundColor: mobileTokens.colors.brandBlack,
    borderRadius: 50,
    paddingHorizontal: 28,
    paddingVertical: 14,
    minWidth: 180,
    alignItems: "center",
  },
  addToBagLabel: {
    fontSize: 15,
    fontWeight: "500",
    color: mobileTokens.colors.pureWhite,
  },
  utilityLink: {
    fontSize: 14,
    color: mobileTokens.colors.descriptionGray,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.2)",
  },
  sheet: {
    backgroundColor: mobileTokens.colors.pureWhite,
    borderTopLeftRadius: mobileTokens.radius.bottomSheet,
    borderTopRightRadius: mobileTokens.radius.bottomSheet,
    ...mobileTokens.shadow.sheet,
  },
  sheetHeader: {
    backgroundColor: mobileTokens.colors.sheetHeaderGray,
    borderTopLeftRadius: mobileTokens.radius.bottomSheet,
    borderTopRightRadius: mobileTokens.radius.bottomSheet,
    paddingVertical: 12,
    alignItems: "center",
  },
  dragHandle: {
    width: 40,
    height: 4,
    borderRadius: 4,
    backgroundColor: "#D1D5DB",
  },
  sizeRow: {
    height: 52,
    borderBottomWidth: 1,
    borderBottomColor: mobileTokens.colors.borderDefault,
    paddingHorizontal: 20,
    flexDirection: "row",
    alignItems: "center",
  },
  sizeCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1.5,
    borderColor: mobileTokens.colors.brandBlack,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: mobileTokens.colors.pureWhite,
  },
  sizeCircleSelected: {
    backgroundColor: mobileTokens.colors.brandBlack,
  },
  sizeLabel: {
    color: mobileTokens.colors.brandBlack,
    fontSize: 15,
  },
  sizeLabelSelected: {
    color: mobileTokens.colors.pureWhite,
  },
  rowSpacer: {
    flex: 1,
  },
  urgency: {
    color: mobileTokens.colors.urgencyGold,
    fontSize: 13,
  },
});
