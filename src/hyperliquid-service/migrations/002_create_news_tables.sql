-- Crypto news and sentiment analysis tables
-- Run against your Supabase project via the SQL editor or psql.

-- ==========================================================================
-- News table: one row per article, with sentiment scores.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS crypto_news (
    id              BIGSERIAL       PRIMARY KEY,
    coin            TEXT            NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_news_coin
    ON crypto_news (coin, collected_at DESC);

-- ==========================================================================
-- Sentiment summary: aggregated sentiment per coin per time period.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS crypto_sentiment_summary (
    id              BIGSERIAL       PRIMARY KEY,
    coin            TEXT            NOT NULL,
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

    UNIQUE (coin, period_start)
);

CREATE INDEX IF NOT EXISTS idx_summary_coin
    ON crypto_sentiment_summary (coin, period_start DESC);
