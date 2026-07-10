# 🥬 FreshAlert — 제철 농식품 가격 알림 서비스 기획서

> **목표**: 소비자가 제철 농식품을 최적의 타이밍에 저렴하게 구매할 수 있도록,  
> 실시간 도매시장 데이터를 분석하여 **맞춤형 알림**을 제공한다.

---

## 📋 목차

1. [서비스 개요](#1-서비스-개요)
2. [활용 공공데이터 선정](#2-활용-공공데이터-선정)
3. [단기 기획 — 농식품 알림 서비스](#3-단기-기획--농식품-알림-서비스)
4. [장기 기획 — 산지직송 쇼핑몰](#4-장기-기획--산지직송-쇼핑몰)
5. [기술 아키텍처](#5-기술-아키텍처)
6. [데이터 파이프라인](#6-데이터-파이프라인)
7. [로드맵 & 마일스톤](#7-로드맵--마일스톤)

---

## 1. 서비스 개요

### 1.1 핵심 가치

| 구분 | 설명 |
|------|------|
| **Who** | 합리적 소비를 원하는 일반 소비자 (주부, 자취생, 가정 요리사) |
| **What** | 제철 농식품이 평소보다 저렴해진 시점을 실시간으로 알려줌 |
| **How** | 도매시장 경락가격 + 소매가격 데이터를 분석, 가격 하락/물량 급증 감지 → 푸시 알림 |
| **Why** | 소비자는 가격 비교에 시간을 쓰지 않고도 최적 타이밍에 구매 가능 |

### 1.2 핵심 기능 3가지

1. **추천 알림** — AI가 현재 시점의 "가성비 TOP" 품목을 선별하여 알림
2. **키워드 등록 알림** — 사용자가 직접 등록한 품목(예: "딸기", "고등어")의 가격 하락 시 알림
3. **카테고리 북마크 알림** — 관심 카테고리(예: "엽경채류", "감귤류")를 구독하여 해당 카테고리 내 최적 구매 조건 알림

---

## 2. 활용 공공데이터 선정

### 2.1 1차 데이터 (핵심 — 농림축산식품부 도매시장 데이터)

| # | API명 | 식별자 | 용도 | 우선순위 |
|---|--------|--------|------|----------|
| 1 | **도매시장 실시간 경락 정보** | TI_WHLSL_MRKT_RLTM_AUC_INFO | 실시간 낙찰가 모니터링, 가격 급락 감지 | ⭐⭐⭐ |
| 2 | **도매시장 정산 가격 정보** | TI_WHLSL_MRKT_CLCLN_PRC_INFO | 일별 정산가(평균/최저/최고), 거래량 추적 | ⭐⭐⭐ |
| 3 | **정산가격 기간별 도매시장별 품목별 총물량·총금액** | TI_CLCLN_PRC_WHLSL_MRKT_ITEM | 품목별 물량 추세 분석, 제철 판단 | ⭐⭐⭐ |
| 4 | **도매시장 원천데이터 정산 가격** | TI_WHLSL_MRKT_DATA_CLCLN_PRC | 개별 거래 단위 상세 데이터 (출하자, 산지, 등급) | ⭐⭐ |
| 5 | **정산가격 기간별 도매시장별 총물량·총금액** | TI_CLCLN_PRC_WHLSL_MRKT | 시장 전체 유통량 추세 | ⭐⭐ |
| 6 | **정산가격 기간별 법인별 품목별 총물량·총금액** | TI_CLCLN_PRC_CORP_ITEM | 법인별 가격 비교 | ⭐ |
| 7 | **도매시장 산지공판장 정산 가격** | TI_MD_JIMKT_CLCLN_PRC | 산지 직거래 가격 비교 | ⭐ |

### 2.2 참조 코드 데이터

| API명 | 용도 |
|--------|------|
| 도매시장 코드 | 시장 식별 (서울가락: 110001, 서울강서: 110008 등) |
| 법인 코드 | 법인 식별 |
| 등급·단위·포장·크기·산지·품목 코드 | 품목 분류 체계 매핑 |
| 농수축산물 표준코드(2015) | 전체 품목 분류 기준 |

### 2.3 2차 데이터 (보완 — KAMIS 농산물유통정보)

| # | API명 | 용도 | 우선순위 |
|---|--------|------|----------|
| 1 | **일별 품목별 소매가격** | 소비자 체감가격 추적 | ⭐⭐⭐ |
| 2 | **일별 품목별 도매가격** | 도매가 교차검증 | ⭐⭐ |
| 3 | **지역별 품목별 도·소매가격정보** | 지역별 가격 차이 분석 | ⭐⭐ |
| 4 | **최근 가격추이 조회** | 월/연 평균가 대비 현재가 비교 | ⭐⭐⭐ |
| 5 | **농축수산물 품목 및 등급 코드표** | 품목 코드 매핑 | ⭐⭐ |

### 2.4 3차 데이터 (자체 구축)

| 데이터 | 구축 방법 | 용도 |
|--------|-----------|------|
| **제철 캘린더** | 농촌진흥청 자료 + 도매시장 물량 패턴 분석 | 품목별 제철 기간 판단 |
| **품목별 가격 기준선** | 3년치 정산데이터 평균/표준편차 계산 | "저렴함"의 기준 설정 |
| **이상치 탐지 모델** | 시계열 분석 (이동평균, Z-score) | 가격 급락 감지 |

---

## 3. 단기 기획 — 농식품 알림 서비스

### 3.1 서비스 구조

```
┌─────────────────────────────────────────────────┐
│                 FreshAlert App                    │
├─────────────────────────────────────────────────┤
│  [추천 알림]   [키워드 알림]   [카테고리 북마크]    │
│                                                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐  │
│  │ 오늘의     │ │ 내 키워드  │ │ 내 카테고리    │  │
│  │ BEST 5    │ │ 가격 현황  │ │ 구독 현황     │  │
│  └───────────┘ └───────────┘ └───────────────┘  │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │         가격 추이 그래프 / 상세 정보          │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 3.2 기능 상세

#### 기능 A: 추천 알림 (Daily Best)

| 항목 | 상세 |
|------|------|
| **트리거** | 매일 오전 7시 (전일 정산 데이터 기반) |
| **알고리즘** | ① 전일 물량 상위 30% 품목 필터 → ② 30일 이동평균 대비 가격 하락률 계산 → ③ 제철 여부 가산점 → ④ 종합 점수 TOP 5 선정 |
| **알림 내용** | 품목명, 현재가(kg당), 30일 평균 대비 하락률(%), 제철 여부 뱃지 |
| **사용자 액션** | 알림 탭 → 품목 상세 → 가격 추이 그래프 |

**추천 점수 산출 공식:**
```
Score = (물량 증가율 × 0.3) + (가격 하락률 × 0.4) + (제철 보너스 × 0.3)

- 물량 증가율: (금일물량 - 7일평균물량) / 7일평균물량
- 가격 하락률: (30일평균가 - 금일가) / 30일평균가
- 제철 보너스: 제철이면 1.0, 아니면 0.0
```

#### 기능 B: 키워드 등록 알림

| 항목 | 상세 |
|------|------|
| **등록 방식** | 검색창에 품목명 입력 → 자동완성 → 등록 (최대 20개) |
| **트리거 조건** | ① 가격이 사용자 설정 임계값 이하 도달 시 OR ② 30일 평균 대비 N% 이상 하락 시 |
| **임계값 설정** | 기본: 30일 평균 대비 -15% / 사용자 커스텀 가능 (-5% ~ -50%) |
| **알림 주기** | 조건 충족 시 즉시 (1일 최대 3회 동일 품목) |
| **알림 내용** | "[딸기] 지금 사면 좋아요! 🍓 현재 kg당 12,500원 (평균 대비 -22%)" |

**키워드 데이터 모델:**
```json
{
  "userId": "user_001",
  "keyword": "딸기",
  "itemCode": { "large": "01", "mid": "01", "small": "001" },
  "threshold": {
    "type": "percentage",     // "percentage" | "absolute"
    "value": -15,             // 30일 평균 대비 -15%
    "absolutePrice": null     // 또는 특정 가격(원/kg)
  },
  "notifyTime": ["07:00", "12:00", "18:00"],
  "enabled": true,
  "createdAt": "2026-07-10T00:00:00Z"
}
```

#### 기능 C: 카테고리 북마크 알림

| 항목 | 상세 |
|------|------|
| **카테고리 목록** | 대분류 기준 (채소류, 과일류, 수산물, 축산물 등) + 중분류 세부 선택 |
| **등록 방식** | 카테고리 브라우저 → 관심 카테고리 토글 ON |
| **트리거** | 해당 카테고리 내 품목 중 추천 점수 상위 3개가 임계값 초과 시 |
| **알림 내용** | "[과일류] 이번 주 BEST: 수박(-30%), 참외(-22%), 자두(-18%)" |
| **알림 주기** | 주 2회 (월/목) 또는 조건 충족 시 |

**카테고리 분류 체계:**
```
대분류(LARGE)     중분류(MID)            예시 품목
──────────────────────────────────────────────────
채소류(01)        엽경채류(01)           배추, 시금치, 상추
                  과채류(02)            토마토, 오이, 호박
                  근채류(03)            무, 당근, 감자
                  양채류(04)            양배추, 브로콜리
과일류(02)        인과류(01)            사과, 배
                  감귤류(02)            귤, 오렌지, 레몬
                  핵과류(03)            복숭아, 자두, 체리
                  장과류(04)            딸기, 포도, 블루베리
수산물(03)        어류(01)              고등어, 갈치, 오징어
                  패류(02)              굴, 조개, 전복
축산물(04)        소(01)                한우, 육우
                  돼지(02)              삼겹살, 목살
                  닭(03)                닭, 오리
```

### 3.3 사용자 여정 (User Journey)

```
[첫 사용]
  ├─ 앱 설치 → 관심 카테고리 선택 (온보딩)
  ├─ 키워드 3개 추천 등록 (인기 품목 기반)
  └─ 추천 알림 기본 활성화

[일상 사용]
  ├─ 오전 7시: "오늘의 추천" 푸시 알림 수신
  │   └─ 탭 → 앱 진입 → 상세 가격 확인
  ├─ 수시: 키워드 등록 품목 가격 하락 알림
  │   └─ 탭 → 근처 마트/시장 연결 (장기 기능)
  └─ 월/목: 카테고리 위클리 리포트 알림
      └─ 탭 → 카테고리 내 TOP 3 확인

[심화 사용]
  ├─ 가격 추이 그래프 확인 → 구매 결정
  ├─ 키워드 임계값 세밀 조정
  └─ 제철 캘린더 확인 → 장보기 계획
```

### 3.4 알림 발송 로직 (상세 플로우)

```
[매일 06:00] 데이터 수집 Batch
  │
  ├─ API 호출: 도매시장 정산 가격 (전일)
  ├─ API 호출: KAMIS 소매 가격
  └─ DB 저장: price_history 테이블
      │
[매일 06:30] 분석 Batch
  │
  ├─ 30일 이동평균 계산
  ├─ 물량 증가율 계산
  ├─ 가격 하락률 계산
  ├─ 제철 보너스 부여
  └─ 추천 점수 산출 → daily_recommendation 테이블
      │
[매일 07:00] 알림 발송
  │
  ├─ [추천 알림] TOP 5 → 전체 사용자 발송
  ├─ [키워드 알림] 임계값 초과 품목 → 해당 사용자 발송
  └─ [카테고리 알림] 월/목 → 구독 사용자 발송
```

### 3.5 화면 설계 (Wireframe)

#### 3.5.1 메인 화면

```
┌─────────────────────────────────┐
│  FreshAlert 🥬        ⚙️ 👤    │
├─────────────────────────────────┤
│                                  │
│  📢 오늘의 추천 (7/10 기준)       │
│  ┌─────────────────────────────┐│
│  │ 1. 🍉 수박    ▼30%  제철🏷️  ││
│  │ 2. 🥒 오이    ▼25%  제철🏷️  ││
│  │ 3. 🍑 복숭아  ▼22%  제철🏷️  ││
│  │ 4. 🥬 상추    ▼18%         ││
│  │ 5. 🧅 양파    ▼15%         ││
│  └─────────────────────────────┘│
│                                  │
│  🔑 내 키워드 (3/20)             │
│  ┌──────┐ ┌──────┐ ┌──────┐    │
│  │ 딸기  │ │ 사과  │ │고등어│    │
│  │ 대기중│ │ ▼12% │ │ ▼8% │    │
│  └──────┘ └──────┘ └──────┘    │
│                       [+ 추가]   │
│                                  │
│  📁 내 카테고리                   │
│  ┌───────────┐ ┌───────────┐    │
│  │ 🥗 채소류  │ │ 🍎 과일류  │    │
│  │ TOP: 오이  │ │ TOP: 수박  │    │
│  └───────────┘ └───────────┘    │
│                                  │
├─────────────────────────────────┤
│  [홈]   [검색]   [알림]   [MY]   │
└─────────────────────────────────┘
```

#### 3.5.2 품목 상세 화면

```
┌─────────────────────────────────┐
│  ← 수박 상세                     │
├─────────────────────────────────┤
│                                  │
│  🍉 수박 (과일류 > 참외류)         │
│  ──────────────────────────────  │
│  현재가: 8,500원/kg               │
│  30일 평균: 12,200원/kg           │
│  하락률: -30.3% ⬇️               │
│  제철: 6월~8월 🏷️ 지금이 제철!    │
│                                  │
│  📈 가격 추이 (최근 30일)          │
│  ┌─────────────────────────────┐│
│  │ 12k ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ││
│  │      ╲                       ││
│  │ 10k    ╲   ╱╲               ││
│  │          ╲╱    ╲             ││
│  │  8k              ╲___●      ││
│  │  6/10     6/20     7/1  7/10││
│  └─────────────────────────────┘│
│                                  │
│  📊 물량 추이 (거래량)            │
│  ┌─────────────────────────────┐│
│  │  ████ ████ ██████ ████████  ││
│  │  6/10  6/20   7/1    7/10  ││
│  └─────────────────────────────┘│
│                                  │
│  🏪 주요 도매시장 가격 비교        │
│  ┌─────────────────────────────┐│
│  │ 가락시장   8,200원  ▼32%    ││
│  │ 강서시장   8,800원  ▼28%    ││
│  │ 부산엄궁   7,900원  ▼35%    ││
│  └─────────────────────────────┘│
│                                  │
│  [🔔 키워드 등록]  [📁 북마크]     │
│                                  │
└─────────────────────────────────┘
```

### 3.6 데이터베이스 설계

```sql
-- 품목 마스터
CREATE TABLE items (
    item_id         SERIAL PRIMARY KEY,
    large_code      VARCHAR(4),       -- 대분류 코드
    mid_code        VARCHAR(4),       -- 중분류 코드
    small_code      VARCHAR(4),       -- 소분류 코드
    large_name      VARCHAR(50),      -- 대분류명
    mid_name        VARCHAR(50),      -- 중분류명
    small_name      VARCHAR(50),      -- 소분류명
    season_start    INTEGER,          -- 제철 시작월 (1-12)
    season_end      INTEGER,          -- 제철 종료월 (1-12)
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 일별 가격 이력
CREATE TABLE price_history (
    id              SERIAL PRIMARY KEY,
    item_id         INTEGER REFERENCES items(item_id),
    market_code     VARCHAR(10),      -- 도매시장 코드
    sale_date       DATE NOT NULL,
    avg_price       INTEGER,          -- 평균가 (원/kg)
    min_price       INTEGER,          -- 최저가
    max_price       INTEGER,          -- 최고가
    total_qty       INTEGER,          -- 총물량 (kg)
    total_amt       BIGINT,           -- 총금액 (원)
    data_source     VARCHAR(20),      -- 'MAFRA' | 'KAMIS'
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 실시간 경락 데이터
CREATE TABLE realtime_auction (
    id              SERIAL PRIMARY KEY,
    item_id         INTEGER REFERENCES items(item_id),
    market_code     VARCHAR(10),
    auction_date    DATE,
    auction_time    TIME,
    cost            INTEGER,          -- 경락가
    qty             INTEGER,          -- 물량
    grade           VARCHAR(10),      -- 등급
    origin          VARCHAR(50),      -- 산지
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 일별 분석 결과
CREATE TABLE daily_analysis (
    id              SERIAL PRIMARY KEY,
    item_id         INTEGER REFERENCES items(item_id),
    analysis_date   DATE,
    avg_30d         INTEGER,          -- 30일 이동평균
    price_drop_rate DECIMAL(5,2),     -- 가격 하락률 (%)
    qty_increase    DECIMAL(5,2),     -- 물량 증가율 (%)
    is_season       BOOLEAN,          -- 제철 여부
    recommend_score DECIMAL(5,3),     -- 추천 점수 (0~1)
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 사용자
CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    email           VARCHAR(100) UNIQUE,
    nickname        VARCHAR(50),
    push_token      TEXT,             -- FCM token
    notify_time     TIME DEFAULT '07:00',
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 키워드 구독
CREATE TABLE keyword_subscriptions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(user_id),
    item_id         INTEGER REFERENCES items(item_id),
    threshold_type  VARCHAR(20),      -- 'percentage' | 'absolute'
    threshold_value DECIMAL(10,2),    -- -15 (%) 또는 12000 (원)
    enabled         BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 카테고리 구독
CREATE TABLE category_subscriptions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(user_id),
    large_code      VARCHAR(4),
    mid_code        VARCHAR(4),       -- NULL이면 대분류 전체 구독
    notify_days     VARCHAR(20) DEFAULT 'MON,THU',
    enabled         BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 알림 이력
CREATE TABLE notifications (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(user_id),
    type            VARCHAR(20),      -- 'recommend' | 'keyword' | 'category'
    title           VARCHAR(200),
    body            TEXT,
    item_id         INTEGER,
    sent_at         TIMESTAMP DEFAULT NOW(),
    read_at         TIMESTAMP
);
```

### 3.7 API 설계 (백엔드)

```yaml
# 인증
POST   /api/v1/auth/register          # 회원가입
POST   /api/v1/auth/login             # 로그인
POST   /api/v1/auth/push-token        # 푸시 토큰 등록

# 추천
GET    /api/v1/recommendations/today   # 오늘의 추천 TOP 5
GET    /api/v1/recommendations/history # 과거 추천 이력

# 품목
GET    /api/v1/items/search?q={query}  # 품목 검색 (자동완성)
GET    /api/v1/items/{itemId}          # 품목 상세
GET    /api/v1/items/{itemId}/prices   # 품목 가격 추이
GET    /api/v1/items/{itemId}/markets  # 시장별 가격 비교

# 키워드 구독
GET    /api/v1/keywords                # 내 키워드 목록
POST   /api/v1/keywords                # 키워드 등록
PUT    /api/v1/keywords/{id}           # 임계값 수정
DELETE /api/v1/keywords/{id}           # 키워드 삭제

# 카테고리 구독
GET    /api/v1/categories              # 전체 카테고리 목록
GET    /api/v1/categories/subscribed   # 내 구독 카테고리
POST   /api/v1/categories/subscribe    # 카테고리 구독
DELETE /api/v1/categories/subscribe/{id} # 구독 해제

# 알림
GET    /api/v1/notifications           # 알림 이력
PUT    /api/v1/notifications/{id}/read # 읽음 처리

# 제철 정보
GET    /api/v1/seasons/current         # 현재 제철 품목
GET    /api/v1/seasons/calendar        # 월별 제철 캘린더
```

### 3.8 알림 메시지 템플릿

```
[추천 알림]
제목: "🥬 오늘의 추천 5종이 도착했어요!"
본문: "수박(-30%), 오이(-25%)... 제철 채소가 역대급 저렴해요"

[키워드 알림]
제목: "🍓 딸기가 목표 가격에 도달했어요!"
본문: "현재 12,500원/kg (평균 대비 -22%) — 지금이 구매 적기!"

[카테고리 알림]
제목: "🍎 과일류 이번 주 BEST 3"
본문: "수박(-30%), 참외(-22%), 자두(-18%) — 여름 과일 대폭 하락"
```

---

## 4. 장기 기획 — 산지직송 쇼핑몰

### 4.1 서비스 확장 개요

```
┌────────────────────────────────────────────────────┐
│              FreshAlert → FreshMarket              │
├────────────────────────────────────────────────────┤
│                                                    │
│  [알림 서비스]  →  [가격 비교]  →  [바로 구매]      │
│                                                    │
│  소비자 ←────── 매칭 ──────→ 판매자(농가/산지)      │
│                                                    │
│  • 실시간 가격 기반 자동 매칭                        │
│  • 산지 직송으로 유통 마진 절감                      │
│  • 공동구매 시스템으로 물량 확보                     │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 4.2 핵심 기능

| 기능 | 설명 |
|------|------|
| **판매자 등록** | 농가/산지 직매인이 상품 등록 (품목, 수량, 희망가격, 배송 가능 지역) |
| **자동 매칭** | 소비자 키워드/카테고리와 판매자 상품 자동 매칭 |
| **공동구매** | 일정 인원 모집 시 대량 구매 할인 → 산지 직송 |
| **가격 보장** | 도매시장 실시간 가격 기반 적정 가격 가이드라인 제시 |
| **리뷰/평점** | 신선도, 배송 품질, 가격 만족도 평가 |
| **정기 배송** | 제철 과일/채소 정기 구독 서비스 |

### 4.3 비즈니스 모델

```
수익원:
├── 거래 수수료 (3~5%)
├── 판매자 프리미엄 노출 광고
├── 정기구독 서비스 수수료
└── 데이터 분석 리포트 (B2B)
```

### 4.4 장기 로드맵

| Phase | 기간 | 내용 |
|-------|------|------|
| Phase 1 | 단기 출시 후 3개월 | 판매자 파트너십 확보 (농협, 산지조합) |
| Phase 2 | +3개월 | 쇼핑몰 MVP (직거래 연결, 결제) |
| Phase 3 | +3개월 | 공동구매, 정기배송 |
| Phase 4 | +6개월 | 풀필먼트, 당일배송, AI 추천 고도화 |

---

## 5. 기술 아키텍처

### 5.1 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  iOS App  │  │Android App│  │  Web App  │                  │
│  │ (React   │  │ (React   │  │ (Next.js) │                  │
│  │  Native) │  │  Native) │  │           │                  │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘                  │
└────────┼──────────────┼─────────────┼───────────────────────┘
         │              │             │
         ▼              ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  FastAPI (Python) / Authentication / Rate Limiting      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                    Service Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Price    │  │ Alert    │  │ Recommend │  │ User     │   │
│  │ Service  │  │ Service  │  │ Service   │  │ Service  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                    Data Layer                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │PostgreSQL│  │  Redis   │  │  S3/CDN  │  │  FCM     │   │
│  │(가격이력) │  │(캐시/큐) │  │(정적파일)│  │(푸시알림)│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│               Data Pipeline Layer                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Scheduler (Cron) → Collector → Analyzer → Notifier  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────┐  ┌──────────┐                                 │
│  │ MAFRA    │  │  KAMIS   │  ← 공공데이터 API               │
│  │ API      │  │  API     │                                 │
│  └──────────┘  └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 기술 스택

| 계층 | 기술 | 선택 이유 |
|------|------|-----------|
| **Mobile** | React Native + Expo | 크로스 플랫폼, 빠른 개발 |
| **Web** | Next.js 14 | SSR, SEO, 빠른 로딩 |
| **Backend** | FastAPI (Python) | 비동기, 데이터 분석 라이브러리 호환 |
| **Database** | PostgreSQL | 시계열 데이터, JSON 지원, 안정성 |
| **Cache** | Redis | 실시간 가격 캐싱, 알림 큐 |
| **Push** | Firebase Cloud Messaging | 크로스 플랫폼 푸시 |
| **Scheduler** | Celery + Redis | 배치 작업 스케줄링 |
| **Deploy** | AWS (ECS/RDS) 또는 Vercel + Supabase | 확장성 |
| **Analytics** | Pandas + NumPy | 가격 분석, 이상치 탐지 |

---

## 6. 데이터 파이프라인

### 6.1 수집 프로세스

```python
# 수집 스케줄 (예시)
COLLECTION_SCHEDULE = {
    "realtime_auction": "*/30 * * * *",    # 30분마다 (개장 시간)
    "daily_settlement": "0 6 * * *",        # 매일 06:00 (전일 정산)
    "kamis_retail":     "0 7 * * *",        # 매일 07:00 (소매가)
    "market_codes":     "0 0 1 * *",        # 월 1회 (코드 갱신)
}
```

### 6.2 분석 프로세스

```python
# 가격 분석 파이프라인
def analyze_daily():
    """매일 06:30 실행"""
    
    # 1. 30일 이동평균 계산
    moving_avg = calculate_moving_average(days=30)
    
    # 2. 가격 하락률
    price_drop = (moving_avg - today_price) / moving_avg * 100
    
    # 3. 물량 증가율
    qty_increase = (today_qty - avg_7d_qty) / avg_7d_qty * 100
    
    # 4. 제철 보너스
    is_season = check_season(item_code, current_month)
    
    # 5. 종합 점수
    score = (
        normalize(qty_increase) * 0.3 +
        normalize(price_drop) * 0.4 +
        (1.0 if is_season else 0.0) * 0.3
    )
    
    return score
```

### 6.3 이상치 탐지

```python
def detect_price_anomaly(item_id, current_price):
    """Z-score 기반 가격 급락 감지"""
    history = get_price_history(item_id, days=90)
    mean = history.mean()
    std = history.std()
    
    z_score = (current_price - mean) / std
    
    # Z-score < -2: 유의미한 가격 하락
    # Z-score < -3: 극단적 가격 하락 (즉시 알림)
    if z_score < -3:
        return "CRITICAL_DROP"
    elif z_score < -2:
        return "SIGNIFICANT_DROP"
    return "NORMAL"
```

---

## 7. 로드맵 & 마일스톤

### 7.1 단기 (MVP 출시까지)

| Week | 마일스톤 | 상세 |
|------|----------|------|
| W1-2 | **데이터 수집 구축** | API 키 발급, 수집기 개발, 코드 테이블 구축 |
| W3-4 | **분석 엔진 개발** | 이동평균, 이상치 탐지, 추천 점수 알고리즘 |
| W5-6 | **백엔드 API 개발** | FastAPI 서버, DB 구축, 인증 |
| W7-8 | **알림 시스템** | FCM 연동, 알림 스케줄러, 템플릿 |
| W9-10 | **프론트엔드 개발** | React Native 앱 (메인, 상세, 설정) |
| W11-12 | **테스트 & 출시** | 베타 테스트, 앱스토어 출시 |

### 7.2 장기

| Quarter | 마일스톤 |
|---------|----------|
| Q1 (출시 후) | 사용자 피드백 반영, 알고리즘 고도화, 웹 버전 |
| Q2 | 판매자 파트너십, 쇼핑몰 MVP |
| Q3 | 공동구매, 정기배송, 결제 시스템 |
| Q4 | AI 개인화 추천, 레시피 연동, 풀필먼트 |

---

## 부록 A: API 연동 상세

### 공공데이터 API 호출 예시

```python
import httpx

BASE_URL = "http://211.237.50.150:7080/openapi"
API_KEY = "발급받은_키"

async def fetch_realtime_auction(sale_date: str, market_code: str):
    """실시간 경락 정보 조회"""
    url = f"{BASE_URL}/{API_KEY}/json/Grid_20240625000000000654_1/1/1000"
    params = {
        "SALEDATE": sale_date,    # "20260710"
        "WHSALCD": market_code,   # "110001" (서울가락)
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        return data["Grid_20240625000000000654_1"]["row"]


async def fetch_settlement_price(sale_date: str, market_code: str):
    """정산 가격 정보 조회"""
    url = f"{BASE_URL}/{API_KEY}/json/Grid_20240625000000000653_1/1/1000"
    params = {
        "SALEDATE": sale_date,
        "WHSALCD": market_code,
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        return data["Grid_20240625000000000653_1"]["row"]


async def fetch_item_volume(regist_date: str, large: str = None, mid: str = None):
    """기간별 도매시장별 품목별 총물량·총금액"""
    url = f"{BASE_URL}/{API_KEY}/json/Grid_20240625000000000658_1/1/1000"
    params = {"REGIST_DT": regist_date}
    if large:
        params["LARGE"] = large
    if mid:
        params["MID"] = mid
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        return data["Grid_20240625000000000658_1"]["row"]
```

### 주요 도매시장 코드

| 코드 | 시장명 | 비고 |
|------|--------|------|
| 110001 | 서울가락 | 최대 규모 |
| 110008 | 서울강서 | |
| 210001 | 부산엄궁 | |
| 210005 | 부산국제수산 | 수산물 특화 |
| 210009 | 부산반여 | |
| 310101 | 대구 | |
| 320301 | 인천 | |

---

## 부록 B: 제철 캘린더 (기본 데이터)

| 월 | 채소 | 과일 | 수산물 |
|----|------|------|--------|
| 1월 | 시금치, 무, 배추 | 귤, 딸기 | 꼬막, 대구 |
| 2월 | 냉이, 달래, 봄동 | 딸기, 한라봉 | 꼬막, 도미 |
| 3월 | 냉이, 쑥, 미나리 | 딸기 | 조개, 주꾸미 |
| 4월 | 두릅, 취나물, 부추 | 딸기, 참외 | 멍게, 키조개 |
| 5월 | 양배추, 감자, 양파 | 참외, 앵두 | 장어, 전복 |
| 6월 | 오이, 상추, 깻잎 | 수박, 자두, 매실 | 전복, 성게 |
| 7월 | 옥수수, 토마토, 호박 | 수박, 복숭아, 포도 | 전복, 민어 |
| 8월 | 고추, 가지, 옥수수 | 포도, 복숭아, 자두 | 전복, 광어 |
| 9월 | 고구마, 토란 | 사과, 배, 포도 | 꽃게, 대하 |
| 10월 | 무, 배추, 고구마 | 사과, 배, 감 | 꽃게, 대하, 전어 |
| 11월 | 무, 배추, 시금치 | 감, 귤, 유자 | 굴, 과메기 |
| 12월 | 시금치, 무 | 귤, 딸기 | 굴, 방어, 과메기 |

---

> **문서 버전**: v1.0  
> **작성일**: 2026-07-10  
> **작성자**: ASF Data Planning Team
