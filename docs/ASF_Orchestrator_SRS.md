
# 소프트웨어 요구사항 명세서 (SRS)

## 프로젝트명: AI Smart Food Supply Orchestrator (ASF-Orchestrator)

**버전:** 1.0.0

**작성일:** 2026년 6월 6일

**대상 시스템:** AI 기반 초개인화 장보기 추천 및 실시간 동적 공급망 최적화 통합 플랫폼

---

## 1. 개요 (Introduction)

### 1.1 목적 및 범위

본 문서는 농림축산식품 공모전 출품 및 시스템 프로덕션 개발을 위한 'AI Smart Food Supply Orchestrator (ASF-Orchestrator)' 플랫폼의 소프트웨어 요구사항 명세서(SRS)입니다. 본 시스템은 공공 데이터(KAMIS 가격, 생산량, 기상 등)와 사용자 소비 패턴/마이데이터를 실시간 결합·조율(Orchestrate)하여, 소비자에게는 초개인화된 다목적 최적 장바구니를 추천하고, 유통망에는 공급 과잉 해소 및 배송 경로 최적화(VRP)를 지원하는 AI 가동형 백엔드 및 프론트엔드 아키텍처 구현을 목적으로 합니다. 범위는 데이터 수집 파이프라인, AI 모델 서빙 인프라, 비동기 큐 기반 유통 최적화 엔진, B2C 모바일 API 및 B2B 대시보드 API를 포함합니다.

### 1.2 용어 정의 및 약어

| 용어 / 약어                | 정의 및 상세 설명                                                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **ASF-Orchestrator** | AI Smart Food Supply Orchestrator의 약어로, 본 플랫폼 시스템의 공식 명칭입니다.                                                      |
| **TFT**              | Temporal Fusion Transformer. 다변량 시계열 데이터의 장단기 의존성을 학습하기 위해 셀프 어텐션 메커니즘을 사용하는 딥러닝 모델입니다. |
| **VRP**              | Vehicle Routing Problem. 차량의 적재 및 이동 거리를 최소화하는 고도의 조합 최적화 경로 탐색 기법입니다.                              |
| **Feast**            | 머신러닝 파이프라인에서 피처 데이터를 일관되게 관리, 저장, 서빙하기 위한 오픈소스 피처 스토어(Feature Store) 프레임워크입니다.       |
| **Triton**           | Triton Inference Server. GPU/CPU 환경에서 다양한 딥러닝 모델을 고성능으로 병렬 서빙하기 위한 NVIDIA의 인프라 솔루션입니다.           |
| **Dynamic Pricing**  | 시장의 수급 불균형 정도에 따라 실시간으로 가격 및 할인율을 동적으로 보정하는 알고리즘 엔진입니다.                                    |

### 1.3 시스템 참조 구성도

`+-------------------------------------------------------------------------------------------------------------------+ | [KAMIS API] [기상청 API] [마이데이터] --(Airflow ETL)--> [Feast Feature Store] --(gRPC)--> [Triton Inference Server]| |                                                                                                  |                | | [B2C App] <--(REST/HTTPS)--> [Kong API Gateway] <--(gRPC)--> [App-Server (Go)] <--(Redis Cache)  | (Model Sync)   | |                                     |                                                            v                | |                                (RabbitMQ Engine)                                      [TFT / GraphSAGE Engine]    | |                                     v                                                                             | |                           [VRP Solver Core (C++)] <---> [PostgreSQL / PostGIS (Spatial DB)]                       | +-------------------------------------------------------------------------------------------------------------------+ `
---

## 2. 시스템 아키텍처 및 시스템 전체 설명

### 2.1 제품의 조망 (Product Perspective)

본 시스템은 마이크로서비스 아키텍처(MSA)를 채택하여 각 모듈의 확장성과 결합도를 최적화합니다. 대용량 유입 데이터를 분산 처리하기 위해 쿠버네티스(K8s) 상에서 오케스트레이션되며, 실시간성이 요구되는 API 게이트웨이 및 코어 서빙 파트는 Go 언어로 개발되고, 대규모 수치 연산 및 AI 모델 추론 부는 Python 및 C++ 최적화 솔버를 연계하여 하이브리드로 작동합니다.

### 2.2 하드웨어 및 인프라 인터페이스 인터랙션

* **추론 하드웨어:** Triton Inference Server가 가동되는 NVIDIA Tensor Core GPU(T4 또는 A10G 인스턴스) 인터페이스를 사용하여 TFT 및 GraphSAGE 모델의 배치 추론을 가속화합니다.
* **데이터베이스 인터페이스:** 대용량 시계열 및 트랜잭션 처리를 위해 PostgreSQL 16(PostGIS 확장 모듈 포함)과 초고속 데이터 캐싱 및 세션 관리를 위한 Redis 클러스터를 활용합니다.
* **메시지 브로커 인터페이스:** VRP 경로 최적화 및 Dynamic Pricing 스케줄링 등 비동기 고부하 연산 작업을 분산 처리하기 위해 RabbitMQ AMQP 프로토콜을 사용합니다.

### 2.3 사용자 세그먼트 및 주요 제약사항

* **B2C 스마트 소비자:** 저렴하면서 영양학적으로 우수한 맞춤형 장바구니 구성을 즉시 제공받아야 하며, 모바일 환경에서 API 응답 속도는 150ms 이내여야 합니다.
* **B2B 농가 및 지역 유통 센터:** 공급 과잉 예측 정보 및 공동 배송 최적화 경로를 웹 대시보드 상에서 지연 없이 확인해야 하며, 대규모 VRP 연산은 최대 5분 이내에 배치 완료되어야 합니다.
* **시스템 제약사항:** 개인정보 보호법 및 신용정보법(마이데이터 관련)에 의거하여 소비자의 영양 상태 및 결제 이력 데이터는 AES-256 알고리즘으로 암호화하여 DB에 적재하며, 외부 전송 시 TLS 1.3 암호화 터널을 의무 적용합니다.

---

## 3. 기능 요구사항 (Functional Requirements)

### 3.1 [FR-1] 실시간 데이터 파이프라인 및 피처 저장소 (Data Ingestion & Feature Store)

* **[FR-1.1] 수집 자동화:** Apache Airflow 스케줄러를 가동하여 매일 오전 06:00에 국립농산물품질관리원, KAMIS, 기상청 공공데이터를 수집하는 ETL 파이프라인을 작동합니다.
* **[FR-1.2] Feast 피처 적재:** 수집된 원천 시계열 데이터를 결측치 보정(Linear Interpolation) 및 스케일링(Standardization) 처리한 후, Feast Feature Store의 Online Store(Redis) 및 Offline Store(Parquet on GCS)에 동시 싱크합니다.
* **[FR-1.3] 예외 상황 전파:** 수집 중 장애 발생 시 Slack 및 PagerDuty 인터페이스를 통해 시스템 관리자에게 즉시 알림을 발송하고, 최대 3회 자동 재시도(Backoff Retry)를 수행합니다.

### 3.2 [FR-2] TFT 기반 가격 및 수급 예측 엔진 서빙 (Forecasting Engine Serving)

* **[FR-2.1] 단기 시계열 예측:** Triton Inference Server 상에 배포된 PyTorch 기반 Temporal Fusion Transformer(TFT) 모델을 활용하여 매일 아침 품목별 예측 스코어를 생성합니다.
* **[FR-2.2] 입력 피처 추출:** 모델 입력값으로 과거 30일간의 도매가, 기온, 강수량, 반입량, 유통 비용 인덱스 피처를 Feast에서 실시간 Fetch하여 입력 데이터 텐서를 구성합니다.
* **[FR-2.3] 예측 지표 갱신:** 예측 결과값인 분위수(q=[0.1,0.5,0.9]q=[0.1, 0.5, 0.9]**q**=**[**0.1**,**0.5**,**0.9**]**)별 가격 정보 및 공급 과잉 위험 수준 지수(Oversupply Risk Index, 0.0~1.0)를 산출하여 PostgreSQL `forecast_pricing` 테이블에 갱신 기록합니다.

### 3.3 [FR-3] 다목적 최적화 초개인화 추천 시스템 (Multi-Objective Optimization Engine)

* **[FR-3.1] 1차 후보군 생성:** 사용자의 과거 구매 빈도를 기반으로 GraphSAGE 알고리즘을 사용해 1차 후보군 아이템을 필터링합니다.
* **[FR-3.2] 다목적 랭킹 연산:** 1차 후보군을 대상으로 목적 함수 f(u,i)=α⋅Utility(u,i)+β⋅Oversupply(i)−γ⋅FoodMile(i)f(u, i) = \alpha \cdot \text{Utility}(u, i) + \beta \cdot \text{Oversupply}(i) - \gamma \cdot \text{FoodMile}(i)**f**(**u**,**i**)**=**α**⋅**Utility**(**u**,**i**)**+**β**⋅**Oversupply**(**i**)**−**γ**⋅**FoodMile**(**i**)** 연산을 실행하여 상위 NN**N**개 품목 조합을 도출합니다.
* **[FR-3.3] 맞춤 콘텐츠 정렬:** 추천된 아이템 리스트와 매칭되는 대체 요리 레시피 텍스트를 고정 템플릿 및 LLM API를 병렬 가동하여 가구 성격에 맞게 렌더링하고, 결과를 JSON 포맷으로 모바일 API에 서빙합니다.

### 3.4 [FR-4] VRP 기반 친환경 공동 물류 및 경로 최적화 (Logistics Optimization Engine)

* **[FR-4.1] 배송 노드 군집화:** B2C 주문 마감 시각(매일 23:00) 직후, 해당 권역별 배송 위경도 데이터를 PostgreSQL PostGIS 공간 쿼리로 추출하여 인접 행렬(Distance Matrix)을 생성합니다.
* **[FR-4.2] VRP 코어 연산:** C++ 기반의 하이퍼 최적화 VRP 솔버 모듈에 인접 행렬과 배송차량 적재 한계(Capacity Constraint), 차량 기지(Depot) 위치를 입력 파라미터로 주입합니다.
* **[FR-4.3] GIS 경로 생성:** 연산 완료된 최적 노드 방문 순서 및 예상 탄소 절감 비용 리포트를 유통 기사 전용 모바일 앱 및 B2B 웹 대시보드로 전달하며, 이때 지리 정보 시각화를 위해 GeoJSON 포맷의 공간 경로 데이터를 생성하여 전달합니다.

### 3.5 [FR-5] Dynamic Pricing 및 ESG 그린 리워드 제어 시스템 (Dynamic Incentives Engine)

* **[FR-5.1] 동적 할인율 요율 적용:** 상품 원가 데이터에 실시간 공급 과잉률 지수(Oversupply Risk Index)를 맵핑하여 기본 판매가의 최소 5%에서 최대 30% 범위의 동적 할인 혜택을 연산하는 실시간 요율 적용 로직을 작동합니다.
* **[FR-5.2] 탄소 마일리지 계산:** 사용자가 로컬푸드 농산물 혹은 못난이 농산물을 최종 결제 타겟으로 선택 시, 산지 거리(km)당 감소하는 이산화탄소(CO2\text{CO}_2**CO**2) 발생 저감량을 수치화하여 매칭 포인트를 1원 단위로 환산 적립합니다.
* **[FR-5.3] 리워드 지갑 동기화:** 누적된 ESG 그린 리워드는 PostgreSQL `user_wallets` 및 Redis 실시간 캐시에 동시 갱신되어 다음 번 결제 요청에 즉각적인 차감 할인이 가능하도록 설계합니다.

### 3.6 [FR-6] API 게이트웨이 및 코어 인증 (API Gateway & Core Authentication)

* **[FR-6.1] 트래픽 통합 제어:** Kong API Gateway를 프론트 프록시로 배치하여 모든 인바운드 트래픽에 대해 JWT(JSON Web Token) 및 OAuth 2.0 기반 유효성 검증을 필수로 수행합니다.
* **[FR-6.2] 처리율 한계 제어:** 무차별 서비스 대입 공격(DDoS) 방지를 위해 IP당 1분간 최대 호출 횟수를 120회로 제한(Rate Limiting)하고, 임계치 초과 시 HTTP 429 Too Many Requests 에러 코드를 반환합니다.

---

## 4. 외부 인터페이스 요구사항 (External Interface Requirements)

### 4.1 사용자 인터페이스 (User Interfaces)

* **B2C 모바일 인터페이스:** iOS 및 Android 네이티브 크로스 플랫폼(Flutter 기반) 규격으로 설계되며, 뷰포트 크기에 유연하게 대응하는 반응형 그리드를 준수합니다. 주요 화면은 다이내믹 스마트 장바구니 리스트 화면, 영양 및 가계부 리포트 화면, 배송 현황 맵 화면으로 구분됩니다.
* **B2B 웹 관리 인터페이스:** 유통 센터 관리자와 농가를 위한 React.js 기반 웹 대시보드 인터페이스입니다. 해상도 1920×10801920 \times 1080**1920**×**1080** 환경에 최적화되며, 실시간 산지 출하 정보 피드와 GIS 기반의 배송 트럭 최적 경로 매핑 차트(Leaflet/Mapbox 연동)를 메인으로 노출합니다.

### 4.2 소프트웨어 및 시스템 인터페이스

* **공공 데이터 연동 인터페이스:** 농림축산식품부 공공데이터포털 RESTful API와 OpenAPI 표준 포맷(XML/JSON) 통신 규격을 준수하며, 매일 새벽 배치 파이프라인 호출을 통해 데이터를 동기화합니다.
* **결제 게이트웨이 인터페이스:** 국내 주요 PG사 및 토스페이먼츠, 카카오페이 API 규격과 인터랙션하기 위한 웹훅(Webhook) 통신 모듈을 확보하며, 결제 승인 결과 데이터를 암호화 상태로 수신 처리합니다.

---

## 5. 비기능 요구사항 (Non-Functional Requirements)

### 5.1 성능 및 지연시간 요구사항 (Performance & Latency)

* **실시간 API 응답 속도:** B2C 모바일 클라이언트에서 요청하는 장바구니 추천 및 가격 조회 API의 종단간(End-to-End) 응답 속도는 95퍼센타일(p95p95**p**95) 기준 150ms 이하여야 합니다.
* **대량 트랜잭션 동시 처리:** 동시 접속 유저 수 10,000명 기준 시스템 CPU 사용률은 60%를 초과하지 않아야 하며, Kubernetes HPA(Horizontal Pod Autoscaler) 설정 조건에 따라 CPU 임계값 70% 도달 시 Pod 인스턴스를 자동으로 배수 스케일 아웃 처리하도록 지정합니다.
* **예측 연산 데이터 처리 성능:** TFT 모델 추론 및 VRP 알고리즘 연산 수행 배치 타임은 수집 완료 시점으로부터 최대 3분 이내에 배치 처리가 안전하게 완료되어야 합니다.

### 5.2 보안 및 프라이버시 요구사항 (Security & Privacy)

* **데이터 저장소 암호화:** PostgreSQL DB 내에 적재되는 사용자의 이름, 연락처, 기저질환 정보, 집 주소 등 민감한 마이데이터는 DB 블록 수준에서 AES-256 기법으로 대칭키 암호화합니다.
* **네트워크 통신 보안:** 모든 클라이언트와 서버 간 HTTP 통신은 SSL/TLS 1.3을 강제 적용하고, SSL 검증을 통과하지 못한 비암호화 통신(HTTP Port 80) 요청은 강제적으로 HTTPS(Port 443)로 리다이렉트합니다.
* **권한 분리 및 접근 제어:** 어드민 대시보드 접근 및 API 데이터 수집 관리 권한은 사내 계정 및 지자체 공인 파트너십 계정에 한하여 다중인증(MFA) 설정을 필수로 요구합니다.

### 5.3 고가용성 및 복구 요구사항 (Availability & Fault Tolerance)

* **시스템 가용성:** 본 서비스 플랫폼은 연간 99.9% 이상의 가동 가용성(High Availability)을 보장해야 하며, 무중단 배포를 지원하기 위해 Kubernetes 블루-그린(Blue-Green) 또는 롤링 업데이트 배포 방식을 준수합니다.
* **백업 및 재해 복구:** 데이터 유실 방지를 위해 PostgreSQL 마스터 DB 데이터를 주기적으로 읽기 전용 슬레이브(Read-only Replica) DB에 실시간 스트리밍 복제하고, 매일 03:00에 콜드 스토리지(GCS)에 압축 암호화 백업 파일을 업로드합니다. 목표 복구 시간(RTO)은 1시간 이내, 목표 복구 시점(RPO)은 최대 24시간 이전으로 정의합니다.

### 5.4 관측 가능성 및 모니터링 (Observability)

* **메트릭 수집 인프라:** 시스템 내 모든 마이크로서비스는 Prometheus 포맷의 모니터링 메트릭 정보를 `/metrics` 엔드포인트로 실시간 외부에 노출해야 합니다.
* **APM 분산 추적:** Jaeger 및 OpenTelemetry 오픈소스 프로토콜을 백엔드 비즈니스 플로우에 통합하여, 요청 발생 시 트레이스 ID(Trace ID)를 헤더에 포함해 마이크로서비스 간 병목 구역과 지연 발생 구간을 실시간 탐지하고 Grafana 대시보드에 시각화합니다.

---

## 6. 데이터베이스 구조 및 데이터 모델 명세 (Data Architecture)

### 6.1 물리 데이터베이스 스키마 설계 (PostgreSQL DDL)

sql

```
-- 사용자 정보 마이데이터 테이블
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    household_size INT DEFAULT 1,
    health_target_keywords VARCHAR(255)[], -- 기저질환, 식단 조건 (예: 'diabetes', 'keto')
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 농산물 마스터 및 수급 정보 테이블
CREATE TABLE agricultural_products (
    product_code VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category_name VARCHAR(50) NOT NULL,
    origin_location VARCHAR(100) NOT NULL,
    base_unit VARCHAR(10) NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL,
    oversupply_risk_index DECIMAL(3, 2) DEFAULT 0.00, -- 0.00 ~ 1.00 수급 과잉도
    carbon_emissions_factor DECIMAL(5, 2) NOT NULL -- kg CO2 per kg
);

-- 시계열 가격 예측 이력 테이블
CREATE TABLE forecast_pricing (
    forecast_id BIGSERIAL PRIMARY KEY,
    product_code VARCHAR(20) REFERENCES agricultural_products(product_code) ON DELETE CASCADE,
    target_date DATE NOT NULL,
    p10_predicted_price DECIMAL(10, 2) NOT NULL,
    p50_predicted_price DECIMAL(10, 2) NOT NULL,
    p90_predicted_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_forecast UNIQUE (product_code, target_date)
);

-- B2C 주문서 및 ESG 리워드 정산 연동 테이블
CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE RESTRICT,
    total_amount DECIMAL(12, 2) NOT NULL,
    discount_amount DECIMAL(12, 2) DEFAULT 0.00,
    earned_esg_points INT DEFAULT 0,
    delivery_coordinate GEOMETRY(Point, 4326) NOT NULL, -- 공간 지리 인덱스 (Spatial Index)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 공간 쿼리 최적화를 위한 지리적 인덱스 생성
CREATE INDEX idx_orders_delivery_coordinate ON orders USING GIST(delivery_coordinate);
```

### 6.2 Redis 실시간 메모리 키 구조 설계

`# 1. 품목별 실시간 동적 할인 요율 캐시 (TTL: 1시간)
Key: dynamic_discount:product:<product_code>
Type: Hash
Fields:

- current_price: "2450.00"
- discount_rate: "0.15"
- raw_oversupply_index: "0.78"
- updated_at: "2026-06-05T12:00:00Z"

# 2. 사용자별 장바구니 AI 추천 결과 캐시 (TTL: 12시간)

Key: ai_basket:user:<user_id>
Type: String (JSON Encoded String)
Value:
,

    ],
    "expected_esg_points": 350
  }
`
-

## 7. 주요 컴포넌트 인터페이스 API 명세 (API Contracts)

### 7.1 [B2C 모바일] AI 추천 장바구니 조회 및 갱신 API (REST / HTTPS)

* **Endpoint:** `GET /api/v1/recommendation/basket`
* **Headers:** `Authorization: Bearer <JWT_TOKEN>`
* **Query Parameters:** `force_refresh=true` (기존 캐시 우회 및 즉시 신규 실시간 계산 필요 여부)
* **Response (HTTP 200 OK):**

json

```
{
  "status": "success",
  "data": {
    "user_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "basket_id": "c73a884d-2a1f-4cf6-ba64-50a7c936df31",
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
        "unit": "개",
        "original_price": 3000.00,
        "discounted_price": 2400.00,
        "oversupply_risk_level": "HIGH",
        "nutrition_match_reason": "사용자 식이섬유 섭취 최적화 결과 매칭",
        "esg_score_contribution": 150
      },
      {
        "product_code": "AGRI-ONIO-053",
        "product_name": "햇 양파",
        "quantity": 1,
        "unit": "망",
        "original_price": 4500.00,
        "discounted_price": 3150.00,
        "oversupply_risk_level": "VERY_HIGH",
        "nutrition_match_reason": "전체 조리 가이드라인 베이스 양념 필수 식단 구성 매칭",
        "esg_score_contribution": 200
      }
    ],
    "esg_milestone": {
      "equivalent_tree_planting_factor": 0.12,
      "co2_reduction_kg": 2.45
    }
  }
}
```

### 7.2 [B2B 물류] 배송 경로 최적화 API (gRPC / Protocol Buffers)

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

## 8. 부록: 수학적 정밀 수식 및 알고리즘 의사코드 (Mathematical Appendix)

### 8.1 다목적 최적화 탐색 알고리즘 의사코드 (Multi-Objective Greedy Selection)

스마트 장바구니 구성을 위해 다차원적인 가치 평가지표를 결합하는 알고리즘 명세입니다.

S∗=arg⁡max⁡S⊂I,∣S∣≤K∑i∈S(α⋅Utility(u,i)+β⋅Oversupply(i)−γ⋅FoodMile(i))S^* = \arg\max_{S \subset I, |S| \le K} \sum_{i \in S} \left( \alpha \cdot \text{Utility}(u, i) + \beta \cdot \text{Oversupply}(i) - \gamma \cdot \text{FoodMile}(i) \right)**S**∗**=**arg**max**S**⊂**I**,**∣**S**∣**≤**K****∑**i**∈**S****(**α**⋅**Utility**(**u**,**i**)**+**β**⋅**Oversupply**(**i**)**−**γ**⋅**FoodMile**(**i**)**)

python

```
def select_optimized_basket(user_id, candidate_items, k_limit, alpha, beta, gamma):
    """
    다목적 최적화 함수를 기반으로 상위 K개의 장바구니 추천 품목을 그리디 방식으로 최종 선택합니다.

    Parameters:
    - user_id: 사용자 고유 식별 키
    - candidate_items: 추천 가능한 농산물 리스트 (딕셔너리 리스트)
    - k_limit: 장바구니에 담을 아이템의 최대 개수 한도
    - alpha, beta, gamma: 유틸리티, 수급과잉, 푸드마일리지 항목에 대한 정책적 가중치 파라미터
    """
    scored_items = []

    for item in candidate_items:
        # 1. 유저 선호 점수 및 영양 균형 점수 산출
        utility = compute_user_nutrition_utility(user_id, item['product_code'])

        # 2. 실시간 공급 과잉 수준 지수 확보
        oversupply = item['oversupply_risk_index']

        # 3. 로컬푸드 산지로부터 배송지까지의 물류 탄소 발생 거리 가중치 계산
        food_mile = calculate_geographical_distance_km(user_id, item['origin_location'])

        # 4. 종합 스코어 도출 (Multi-Objective Optimization Score)
        total_score = (alpha * utility) + (beta * oversupply) - (gamma * food_mile)

        scored_items.append({
            "product_code": item['product_code'],
            "score": total_score,
            "utility": utility,
            "oversupply": oversupply,
            "food_mile": food_mile
        })

    # 종합 스코어가 가장 높은 순으로 정렬 후 상위 K개 결과 슬라이싱 반환
    scored_items.sort(key=lambda x: x['score'], reverse=True)
    return scored_items[:k_limit]
```
