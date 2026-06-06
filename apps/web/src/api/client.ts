const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface BasketItem {
  product_code: string;
  product_name: string;
  quantity: number;
  unit: string;
  original_price: number;
  discounted_price: number;
  oversupply_risk_level: string;
  nutrition_match_reason: string;
  esg_score_contribution: number;
}

export interface BasketEnvelope {
  status: "success";
  data: {
    user_id: string;
    basket_id: string;
    calculated_at: string;
    summary: {
      total_items_count: number;
      estimated_original_price: number;
      estimated_discounted_price: number;
      total_discount_rate: number;
      estimated_esg_points: number;
    };
    items: BasketItem[];
    esg_milestone: {
      equivalent_tree_planting_factor: number;
      co2_reduction_kg: number;
    };
  };
}

export interface ForecastEnvelope {
  status: "success";
  data: Array<{
    product_code: string;
    target_date: string;
    p10_predicted_price: number;
    p50_predicted_price: number;
    p90_predicted_price: number;
    oversupply_risk_index: number;
  }>;
}

export interface RouteEnvelope {
  status: "success";
  data: {
    warehouse_id: string;
    optimized_routes: Array<{
      route_index: number;
      path_destination_ids: string[];
      total_distance_meters: number;
      total_travel_time_seconds: number;
      co2_emitted_kg: number;
    }>;
    base_co2_reduction_percentage: number;
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function issueToken(userId = "user_dev_01"): Promise<string> {
  const response = await request<{ access_token: string }>("/api/v1/auth/token", {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
  return response.access_token;
}

export async function fetchBasket(token: string): Promise<BasketEnvelope> {
  return request<BasketEnvelope>("/api/v1/recommendation/basket", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function fetchForecasts(): Promise<ForecastEnvelope> {
  return request<ForecastEnvelope>("/api/v1/forecast/pricing");
}

export async function fetchRoute(): Promise<RouteEnvelope> {
  return request<RouteEnvelope>("/api/v1/logistics/route", {
    method: "POST",
    body: JSON.stringify({
      warehouse_id: "WH-SEOUL-01",
      warehouse_coordinate: {
        latitude: 37.5665,
        longitude: 126.978,
      },
      destinations: [
        {
          destination_id: "D-101",
          coordinate: { latitude: 37.572, longitude: 126.99 },
          demand_weight_kg: 14,
        },
        {
          destination_id: "D-205",
          coordinate: { latitude: 37.552, longitude: 126.964 },
          demand_weight_kg: 9,
        },
        {
          destination_id: "D-309",
          coordinate: { latitude: 37.545, longitude: 127.02 },
          demand_weight_kg: 11,
        },
      ],
      vehicle_max_capacity_kg: 20,
    }),
  });
}
