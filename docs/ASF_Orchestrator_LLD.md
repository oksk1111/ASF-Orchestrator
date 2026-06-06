
# [상세 설계 문서] AI Smart Food Supply Orchestrator (ASF-Orchestrator)

## 수요·공급·유통 동적 최적화를 위한 시스템 상세 설계 명세서

---

## 1. 모듈 아키텍처 및 세부 컴포넌트 설계

### 1.1 B2C API 백엔드 서버 (Go) 레이어드 아키텍처

Go 백엔드 서버는 엔터프라이즈 레벨의 트래픽을 처리하기 위해 의존성 역전 원칙(DIP)을 준수하는 클린 레이어드 아키텍처를 채택합니다.

* **Presentation Layer (Delivery):** REST HTTP 엔드포인트와 gRPC 서빙 포트를 기동하며, 외부 입력 패킷 데이터 구조체 바인딩 및 유효성 검증(Validation)을 담당합니다.
* **Business Logic Layer (UseCase):** 플랫폼 비즈니스 규칙의 코어 흐름을 원자적으로 제어하며, 다목적 최적화 알고리즘 컴포넌트와 비동기 이벤트를 오케스트레이션합니다.
* **Data Access Layer (Repository):** PostgreSQL 매퍼(sqlx), Redis 커넥션, Triton Inference Server 호출용 gRPC 클라이언트 어댑터 장치를 구체화하여 상위 레이어에 추상화된 포트 인터페이스를 공급합니다.

### 1.2 AI 추론 및 파이프라인 (Python) 아키텍처

AI 연산 파이프라인은 병목 구간이 대규모 DB 입출력에서 발생하지 않도록 Feature Store 기반의 저지연(Low-latency) 캐시 구조로 제어됩니다.

* **Feature Store Client Interface:** Feast Client를 초기 구동하여, 온라인 분산 캐시 스토리지(Redis Cluster)로부터 추론에 필요한 예측 이력 및 변수 피처 텐서를 10ms 이내에 페치합니다.
* **Triton Client Worker:** Triton Inference Server에 배포된 시계열 수급 예측(TFT) 및 그래프 임베딩 추천(GraphSAGE) 모델의 실행을 가속화하며, Triton gRPC 프레임워크 상에서 동적 배치 처리를 제어합니다.

### 1.3 C++ VRP 솔버 래퍼 설계

고부하 공간 라우팅 조합 최적화 연산을 위해, 메모리 사용량과 SIMD 하드웨어 가속을 활용하는 C++ 컴파일 바이너리 모듈을 통합 제어합니다.

* **Data Model Mapping:** Go/Python에서 생성된 배송 경유 노드 어레이 데이터를 C++ 구조체 `VRPNode`로 원자적 형변환 처리합니다.
* **Solver DLL/SO Integration:** Go 언어의 Cgo 컴파일 기법을 연동하여 네이티브 동적 링크 라이브러리(.so)로 호출하거나, 대규모 연산 시 독립 gRPC 마이크로서비스 데몬 형태로 기동하여 유연하게 트래픽을 분산시킵니다.

---

## 2. 세부 트랜잭션 시퀀스 및 데이터 흐름

### 2.1 초개인화 AI 장바구니 추천 흐름 (B2C)

소비자가 앱 메인 홈 화면에 접근하는 즉시 다목적 선형 최적화 추천 엔진이 연산 작업을 수행하는 실시간 통신 시퀀스입니다.

`[User Client]      [Go API Server]      [Redis Cache]     [Triton AI Server]    [Feast / DB]       |                   |                   |                   |                   |       |-- GET /basket --->|                   |                   |                   |       |                   |--- 1. Check 캐시 ->|                   |                   |       |                   |<-- 캐시 미스 ------|                   |                   |       |                   |                                       |                   |       |                   |--- 2. 피처 데이터 Fetch ─────────────────────────────────>|       |                   |<-- 피처 벡터 수신 ────────────────────────────────────────|       |                   |                                       |                   |       |                   |--- 3. 텐서 변환 및 추론 gRPC 호출 ---->|                   |       |                   |<-- 추론 예측 결과 수신 ---------------|                   |       |                   |                                       |                   |       |                   |--- 4. 다목적 최적화 스코어링 연산 -------|                   |       |                   |--- 5. 결과 캐시 쓰기 ---->|                   |                   |       |<- 200 OK (JSON) --|                   |                   |                   | `

### 2.2 실시간 수급 연동 Dynamic Pricing 및 결제 프로세스

구매 확정 순간에 분산락 제어를 통해 실시간 데이터 무결성을 보장하며, 결제와 포인트 정산을 안전하게 마무리하는 트랜잭션 시퀀스입니다.

`[User Client]      [Go API Server]      [Redis Lock]      [PostgreSQL DB]     [Message Broker]       |                   |                   |                   |                   |       |-- POST /checkout ->|                   |                   |                   |       |                   |--- 1. 분산락 획득 ->|                   |                   |       |                   |<-- Lock OK -------|                   |                   |       |                   |                                       |                   |       |                   |--- 2. DB 트랜잭션 개시 --------------->|                   |       |                   |    - 유저 지갑 차감                   |                   |       |                   |    - 수급 기여 리워드 포인트 적립     |                   |       |                   |    - 주문 기록 삽입                   |                   |       |                   |<-- 트랜잭션 커밋 완료 -----------------|                   |       |                   |                                       |                   |       |                   |--- 3. 분산락 해제 ->|                   |                   |       |                   |                                       |                   |       |                   |--- 4. 비동기 공급망 재고 차감 이벤트 전송 ───────────────>|       |<- 201 Created ----|                                                           | `

### 2.3 대규모 VRP 물류 경로 최적화 및 배치 작업 흐름 (B2B)

일간 주문 처리가 전량 마감되는 매일 23:00 정각에 기동하여 전국 지자체 허브 배차 경로를 실시간 생성 및 파싱하는 지연 없는 배치 프로세스입니다.

`[Airflow Daemon]    [Go Batch Job]     [PostgreSQL GIS]     [RabbitMQ Queue]    [C++ VRP Solver]        |                   |                   |                   |                   |        |-- 23:00 Trigger ->|                   |                   |                   |        |                   |-- 1. 주문 위경도 쿼리 ------------>|                   |        |                   |<-- 노드 데이터 셋 반환 -------------|                   |        |                   |                                       |                   |        |                   |-- 2. 권역별 청크 분할 및 메시지 발행 ->|                   |        |                   |                                       |--- 3. 메시지 컨슘 ->|        |                   |                                       |-- (C++ Cgo Call)->|        |                   |                                       |   VRP 연산 최적화 |        |                   |<-- 4. 최적 경로 GeoJSON 결과 저장 <────────────────────────|        |                   |-- 5. 배송 기사 기기 웹훅 발송 -------->|                   | `
---

## 3. 물리 데이터 모델 및 캐싱 아키텍처 상세

### 3.1 PostgreSQL DDL 및 정규화/인덱스 상세 설계

보안, 가격 예측 시계열 피드백 루프 및 GIS 공간 처리를 효율적으로 지탱하기 위해 최적화된 물리 릴레이션 정의 스키마입니다.

sql

```
-- 1. 사용자 데이터베이스
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    household_size INT NOT NULL DEFAULT 1 CHECK (household_size > 0),
    health_target_keywords VARCHAR(50)[] DEFAULT '{}',
    monthly_budget DECIMAL(10, 2) DEFAULT 500000.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);

-- 2. 농산물 정보 마스터 테이블
CREATE TABLE agricultural_products (
    product_code VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category_name VARCHAR(50) NOT NULL,
    origin_location VARCHAR(100) NOT NULL,
    base_unit VARCHAR(10) NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL CHECK (base_price >= 0),
    oversupply_risk_index DECIMAL(3, 2) NOT NULL DEFAULT 0.00 CHECK (oversupply_risk_index BETWEEN 0.00 AND 1.00),
    carbon_emissions_factor DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_products_category ON agricultural_products(category_name, is_active);
CREATE INDEX idx_products_oversupply ON agricultural_products(oversupply_risk_index DESC) WHERE is_active = TRUE;

-- 3. 고성능 공간 지리 데이터 연동 주문서 테이블
CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    total_amount DECIMAL(12, 2) NOT NULL,
    discount_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    earned_esg_points INT NOT NULL DEFAULT 0,
    delivery_address VARCHAR(255) NOT NULL,
    delivery_coordinate GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
-- 공간 쿼리 속도 보장을 위한 GiST 인덱스 적용
CREATE INDEX idx_orders_delivery_coordinate ON orders USING GIST(delivery_coordinate);
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC);
```

### 3.2 Redis High-Performance 인메모리 스키마 구조

밀리초 단위의 동적 가격 책정 요율과 API 트랜잭션 동시성 격리(Isolation) 처리를 보장하는 분산 키 명세 구조 설계안입니다.

* **동적 할인 정보 해시 스키마:** Key 포맷은 `product:pricing:{product_code}` (TTL: 1800초)이며, Hash 구조 데이터셋으로 관리됩니다. (Fields: `p_price` : float, `d_rate` : float, `risk` : float, `up_ts` : integer).
* **동시성 제어용 분산락 스키마:** Key 포맷은 `lock:order:checkout:{user_id}` (TTL: 5초)이며, 동시 진입으로 인한 포인트 및 재고 더블 디핑 방지를 위해 원자적 Redis 명령어 `SET key value NX PX 5000` 방식을 준수하여 잠금 장치를 운영합니다.

---

## 4. API 및 프로토콜 상세 스펙 (Contracts)

### 4.1 B2C REST API: 장바구니 추천 조회 인터페이스

* **HTTP Method & Path:** `GET /api/v1/recommendation/basket`
* **Headers:** `Authorization: Bearer <JWT_TOKEN>` 및 `Accept: application/json`
* **Response Body (HTTP 200 OK):**

json

```
{
  "status": "success",
  "data": {
    "basket_id": "c73a884d-2a1f-4cf6-ba64-50a7c936df31",
    "calculated_at": "2026-06-05T15:20:00Z",
    "summary": {
      "total_items_count": 2,
      "estimated_original_price": 7500.00,
      "estimated_discounted_price": 5550.00,
      "total_discount_rate": 0.26,
      "estimated_esg_points": 350
    },
    "items": [
      {
        "product_code": "AGRI-CABB-001",
        "product_name": "유기농 괴산 양배추",
        "quantity": 1,
        "original_price": 3000.00,
        "discounted_price": 2400.00,
        "oversupply_risk_level": "HIGH",
        "esg_score_contribution": 150
      },
      {
        "product_code": "AGRI-ONIO-053",
        "product_name": "햇 양파",
        "quantity": 1,
        "original_price": 4500.00,
        "discounted_price": 3150.00,
        "oversupply_risk_level": "VERY_HIGH",
        "esg_score_contribution": 200
      }
    ]
  }
}
```

### 4.2 B2B gRPC 인터페이스: 물류 최적 경로 계산 프로토콜

```
syntax = "proto3";

package logistics.v1;

option go_package = "github.com/asf-orchestrator/logistics/v1;logisticsv1";

service LogisticsService {
  rpc CalculateRoute(CalculateRouteRequest) returns (CalculateRouteResponse);
}

message Coordinate {
  double latitude = 1;
  double longitude = 2;
}

message DeliveryDestination {
  string destination_id = 1;
  Coordinate coordinate = 2;
  double demand_weight_kg = 3;
}

message CalculateRouteRequest {
  string warehouse_id = 1;
  Coordinate warehouse_coordinate = 2;
  repeated DeliveryDestination destinations = 3;
  double vehicle_max_capacity_kg = 4;
}

message OptimizedRoute {
  int32 route_index = 1;
  repeated string path_destination_ids = 2;
  double total_distance_meters = 3;
  double total_travel_time_seconds = 4;
  double co2_emitted_kg = 5;
}

message CalculateRouteResponse {
  string warehouse_id = 1;
  repeated OptimizedRoute optimized_routes = 2;
  double base_co2_reduction_percentage = 3;
}
```

---

## 5. 핵심 알고리즘 소스코드 레벨 구현

### 5.1 다목적 최적화 탐색 엔진 (Python)

아래 스크립트는 실시간 수급 과잉 상황과 건강 지수, 산지 거리 패널티를 융합하여 목적함수 f(u,i)=α⋅Utility(u,i)+β⋅Oversupply(i)−γ⋅FoodMile(i)f(u, i) = \alpha \cdot \text{Utility}(u, i) + \beta \cdot \text{Oversupply}(i) - \gamma \cdot \text{FoodMile}(i)**f**(**u**,**i**)**=**α**⋅**Utility**(**u**,**i**)**+**β**⋅**Oversupply**(**i**)**−**γ**⋅**FoodMile**(**i**)**를 탐색 수렴시키는 고성능 랭커 모듈입니다.

python

```
import numpy as np

def compute_user_nutrition_utility(user_id: str, product_code: str) -> float:
    # 개인 식단 선호 매칭도 유틸리티 값 산정 모크 함수
    hash_val = hash(user_id + product_code) % 100
    return float(hash_val) / 100.0

def calculate_geographical_distance_km(origin_loc: str) -> float:
    # 산지와 소비자 배송 지경 간의 수리적 연동 반환
    return 15.0 if "괴산" in origin_loc else 120.0

def select_optimized_basket(user_id: str, candidate_items: list, k_limit: int, 
                            alpha: float, beta: float, gamma: float) -> list:
    scored_items = []

    for item in candidate_items:
        # 1. 개인화 영양 궁합 점수 산출
        utility = compute_user_nutrition_utility(user_id, item['product_code'])

        # 2. 푸드 마일리지 패널티 연산 (탄소 발생량)
        distance = calculate_geographical_distance_km(item['origin_location'])
        food_mile_penalty = min(distance / 500.0, 1.0) 

        # 3. 공급 과잉률 매핑
        oversupply = item['oversupply_risk_index']

        # 4. 종합 랭킹 스코어 계산
        total_score = (alpha * utility) + (beta * oversupply) - (gamma * food_mile_penalty)

        scored_items.append({
            "product_code": item['product_code'],
            "score": round(total_score, 4),
            "utility": round(utility, 2),
            "oversupply": round(oversupply, 2),
            "food_mile_penalty": round(food_mile_penalty, 2)
        })

    # 종합 점수 정렬 후 최상위 k개 품목 선정
    scored_items.sort(key=lambda x: x['score'], reverse=True)
    return scored_items[:k_limit]

if __name__ == "__main__":
    test_candidates = [
        {"product_code": "AGRI-CABB-001", "origin_location": "충북 괴산", "oversupply_risk_index": 0.85},
        {"product_code": "AGRI-ONIO-053", "origin_location": "전남 무안", "oversupply_risk_index": 0.95},
        {"product_code": "AGRI-PORK-102", "origin_location": "경기 이천", "oversupply_risk_index": 0.20},
    ]
    result = select_optimized_basket("user_dev_01", test_candidates, 2, alpha=0.4, beta=0.5, gamma=0.1)
    print("선택된 최적 장바구니 큐레이션:", result)
```

### 5.2 Go 도메인 핵심 구조체 정의 (Go)

Go API 코어 레이어의 결합도를 완화하기 위해 정의된 추상 포트 지향 비즈니스 도메인 인터페이스 설계 명세입니다.

go

```
package domain

import (
	"context"
	"time"
)

type Product struct {
	ProductCode         string    `json:"product_code" db:"product_code"`
	ProductName         string    `json:"product_name" db:"product_name"`
	CategoryName        string    `json:"category_name" db:"category_name"`
	OriginLocation      string    `json:"origin_location" db:"origin_location"`
	BaseUnit            string    `json:"base_unit" db:"base_unit"`
	BasePrice           float64   `json:"base_price" db:"base_price"`
	OversupplyRiskIndex float64   `json:"oversupply_risk_index" db:"oversupply_risk_index"`
	CarbonEmissions     float64   `json:"carbon_emissions_factor" db:"carbon_emissions_factor"`
	IsActive            bool      `json:"is_active" db:"is_active"`
	CreatedAt           time.Time `json:"created_at" db:"created_at"`
}

type User struct {
	UserID               string    `json:"user_id" db:"user_id"`
	Email                string    `json:"email" db:"email"`
	PasswordHash         string    `json:"-" db:"password_hash"`
	HouseholdSize        int       `json:"household_size" db:"household_size"`
	HealthTargetKeywords []string  `json:"health_target_keywords" db:"health_target_keywords"`
	MonthlyBudget        float64   `json:"monthly_budget" db:"monthly_budget"`
}

type BasketUseCase interface {
	GetOptimizedBasket(ctx context.Context, userID string) (*BasketResponse, error)
}

type ProductRepository interface {
	FetchActiveCandidates(ctx context.Context) ([]Product, error)
	GetByCode(ctx context.Context, code string) (*Product, error)
}

type BasketItem struct {
	ProductCode          string  `json:"product_code"`
	ProductName          string  `json:"product_name"`
	Quantity             int     `json:"quantity"`
	OriginalPrice        float64 `json:"original_price"`
	DiscountedPrice      float64 `json:"discounted_price"`
	OversupplyRiskLevel  string  `json:"oversupply_risk_level"`
	EsgScoreContribution int     `json:"esg_score_contribution"`
}

type BasketResponse struct {
	BasketID     string       `json:"basket_id"`
	CalculatedAt time.Time    `json:"calculated_at"`
	Items        []BasketItem `json:"items"`
}
```

---

## 6. 프로젝트 디렉토리 레이아웃 및 빌드 구성

엔터프라이즈의 지속적인 배포 편의성과 의존 관계 가시성을 안전하게 추적할 수 있도록 구성된 표준 디렉토리 트리 구조입니다.

`asf-orchestrator-root/ │ ├── cmd/ │   └── api-server/              # Go REST/gRPC 통합 메인 구동 진입점 │       └── main.go │ ├── internal/                    # 컴파일 바이너리 외부 노출 차단 비즈니스 코어 패키지 │   ├── delivery/                # HTTP 라우터 핸들러 및 gRPC 프로토 서버 정의 │   │   ├── http/ │   │   └── grpc/ │   ├── usecase/                 # 도메인 제어 흐름 제어 레이어 │   ├── repository/              # PostgreSQL SQLx 매퍼 및 Redis/Triton 인터페이스 연동 │   └── domain/                  # 핵심 인터페이스 계약 및 엔티티 │ ├── ai-engines/                  # Python 딥러닝 분석 및 Feature Store 디렉토리 │   ├── models/                  # ONNX/PyTorch로 직렬화된 모델 파일 (.onnx / .pt) │   ├── config/                  # Triton Model Config 메타정보 (config.pbtxt) │   ├── train/                   # TFT 모델 트레이닝 파이프라인 │   └── feature_store/           # Feast 피처 메타데이터 정의 (feature_services.yaml) │ ├── solver-vrp/                  # C++ 기반 고성능 라우팅 솔버 서브모듈 │   ├── src/ │   │   ├── main.cpp │   │   └── vrp_optimizer.cpp │   └── CMakeLists.txt │ ├── docker-compose.yml           # 분산 컨테이너 및 Redis/PostgreSQL 기동 명세 └── Makefile                     # 빌드 자동화 및 마이그레이션 스케줄러 매핑 스크립트 `
