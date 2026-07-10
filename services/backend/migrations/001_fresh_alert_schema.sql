-- FreshAlert: 제철 농식품 가격 알림 서비스 스키마
-- Migration 001: Initial schema creation
-- Date: 2026-07-10

BEGIN;

-- 품목 마스터
CREATE TABLE IF NOT EXISTS fa_items (
    item_id         VARCHAR(20) PRIMARY KEY,
    large_code      VARCHAR(4) NOT NULL,
    mid_code        VARCHAR(4) NOT NULL,
    small_code      VARCHAR(4) DEFAULT '',
    large_name      VARCHAR(50) NOT NULL,
    mid_name        VARCHAR(50) NOT NULL,
    small_name      VARCHAR(50) DEFAULT '',
    season_start    INTEGER CHECK (season_start BETWEEN 1 AND 12),
    season_end      INTEGER CHECK (season_end BETWEEN 1 AND 12),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_fa_items_category ON fa_items(large_code, mid_code);
CREATE INDEX idx_fa_items_season ON fa_items(season_start, season_end);

-- 일별 가격 이력
CREATE TABLE IF NOT EXISTS fa_price_history (
    id              BIGSERIAL PRIMARY KEY,
    item_id         VARCHAR(20) NOT NULL REFERENCES fa_items(item_id),
    market_code     VARCHAR(10) NOT NULL,
    market_name     VARCHAR(50),
    sale_date       DATE NOT NULL,
    avg_price       INTEGER NOT NULL,
    min_price       INTEGER,
    max_price       INTEGER,
    total_qty       INTEGER,
    total_amt       BIGINT,
    data_source     VARCHAR(10) NOT NULL CHECK (data_source IN ('MAFRA', 'KAMIS')),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_fa_price_item_date ON fa_price_history(item_id, sale_date DESC);
CREATE INDEX idx_fa_price_market ON fa_price_history(market_code, sale_date DESC);
CREATE UNIQUE INDEX idx_fa_price_unique ON fa_price_history(item_id, market_code, sale_date, data_source);

-- 실시간 경락 데이터
CREATE TABLE IF NOT EXISTS fa_realtime_auction (
    id              BIGSERIAL PRIMARY KEY,
    item_id         VARCHAR(20) NOT NULL REFERENCES fa_items(item_id),
    market_code     VARCHAR(10) NOT NULL,
    market_name     VARCHAR(50),
    auction_date    DATE NOT NULL,
    auction_time    TIME,
    cost            INTEGER NOT NULL,
    qty             INTEGER,
    grade           VARCHAR(20),
    origin          VARCHAR(50),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_fa_auction_item_date ON fa_realtime_auction(item_id, auction_date DESC);
CREATE INDEX idx_fa_auction_market ON fa_realtime_auction(market_code, auction_date DESC);

-- 일별 분석 결과
CREATE TABLE IF NOT EXISTS fa_daily_analysis (
    id              BIGSERIAL PRIMARY KEY,
    item_id         VARCHAR(20) NOT NULL REFERENCES fa_items(item_id),
    analysis_date   DATE NOT NULL,
    avg_30d         INTEGER,
    current_price   INTEGER,
    price_drop_rate DECIMAL(6,2),
    qty_increase_rate DECIMAL(6,2),
    is_season       BOOLEAN DEFAULT FALSE,
    recommend_score DECIMAL(5,3),
    anomaly_status  VARCHAR(20) DEFAULT 'NORMAL',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_fa_analysis_unique ON fa_daily_analysis(item_id, analysis_date);
CREATE INDEX idx_fa_analysis_date_score ON fa_daily_analysis(analysis_date DESC, recommend_score DESC);

-- 사용자 (FreshAlert 전용, 기존 users 확장)
CREATE TABLE IF NOT EXISTS fa_users (
    user_id         VARCHAR(50) PRIMARY KEY,
    email           VARCHAR(100) UNIQUE,
    nickname        VARCHAR(50),
    push_token      TEXT,
    notify_time     TIME DEFAULT '07:00',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 키워드 구독
CREATE TABLE IF NOT EXISTS fa_keyword_subscriptions (
    id              VARCHAR(50) PRIMARY KEY,
    user_id         VARCHAR(50) NOT NULL REFERENCES fa_users(user_id),
    item_id         VARCHAR(20) NOT NULL REFERENCES fa_items(item_id),
    item_name       VARCHAR(100) NOT NULL,
    threshold_type  VARCHAR(20) NOT NULL CHECK (threshold_type IN ('percentage', 'absolute')),
    threshold_value DECIMAL(10,2) NOT NULL,
    enabled         BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_fa_keyword_user ON fa_keyword_subscriptions(user_id, enabled);
CREATE INDEX idx_fa_keyword_item ON fa_keyword_subscriptions(item_id);

-- 카테고리 구독
CREATE TABLE IF NOT EXISTS fa_category_subscriptions (
    id              VARCHAR(50) PRIMARY KEY,
    user_id         VARCHAR(50) NOT NULL REFERENCES fa_users(user_id),
    large_code      VARCHAR(4) NOT NULL,
    large_name      VARCHAR(50) NOT NULL,
    mid_code        VARCHAR(4),
    mid_name        VARCHAR(50),
    notify_days     VARCHAR(30) DEFAULT 'MON,THU',
    enabled         BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_fa_category_user ON fa_category_subscriptions(user_id, enabled);

-- 알림 이력
CREATE TABLE IF NOT EXISTS fa_notifications (
    id              VARCHAR(50) PRIMARY KEY,
    user_id         VARCHAR(50) NOT NULL REFERENCES fa_users(user_id),
    type            VARCHAR(20) NOT NULL CHECK (type IN ('recommend', 'keyword', 'category')),
    title           VARCHAR(200) NOT NULL,
    body            TEXT,
    item_id         VARCHAR(20),
    sent_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at         TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_fa_notifications_user ON fa_notifications(user_id, sent_at DESC);
CREATE INDEX idx_fa_notifications_unread ON fa_notifications(user_id) WHERE read_at IS NULL;

-- 일별 추천 결과
CREATE TABLE IF NOT EXISTS fa_daily_recommendations (
    id              BIGSERIAL PRIMARY KEY,
    rec_date        DATE NOT NULL UNIQUE,
    items_json      JSONB NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_fa_rec_date ON fa_daily_recommendations(rec_date DESC);

COMMIT;
