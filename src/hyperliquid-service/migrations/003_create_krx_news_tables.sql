-- KRX stock news and sentiment analysis tables
-- Run against your Supabase project via the SQL editor or psql.

-- ==========================================================================
-- KRX News table: one row per article, with sentiment scores.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS krx_news (
    id              BIGSERIAL       PRIMARY KEY,
    stock_code      TEXT            NOT NULL,
    stock_name      TEXT            NOT NULL,
    title           TEXT            NOT NULL,
    description     TEXT,
    source          TEXT,
    url             TEXT            UNIQUE,
    published_at    TIMESTAMPTZ,
    sentiment_score NUMERIC,
    sentiment_label TEXT,
    keywords        JSONB           DEFAULT '[]'::jsonb,
    collected_at    TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_krx_news_stock
    ON krx_news (stock_code, collected_at DESC);

-- ==========================================================================
-- KRX Sentiment summary: aggregated sentiment per stock per time period.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS krx_sentiment_summary (
    id              BIGSERIAL       PRIMARY KEY,
    stock_code      TEXT            NOT NULL,
    stock_name      TEXT            NOT NULL,
    period_start    TIMESTAMPTZ     NOT NULL,
    period_end      TIMESTAMPTZ     NOT NULL,
    avg_sentiment   NUMERIC,
    sentiment_label TEXT,
    article_count   INT             DEFAULT 0,
    positive_count  INT             DEFAULT 0,
    negative_count  INT             DEFAULT 0,
    neutral_count   INT             DEFAULT 0,
    top_keywords    JSONB           DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),

    UNIQUE (stock_code, period_start)
);

CREATE INDEX IF NOT EXISTS idx_krx_summary_stock
    ON krx_sentiment_summary (stock_code, period_start DESC);
