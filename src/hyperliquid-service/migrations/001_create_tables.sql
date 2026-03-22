-- Hyperliquid candle and tick storage tables
-- Run against your Supabase project via the SQL editor or psql.

-- ==========================================================================
-- Candle table: one row per closed candle (coin + interval + open_time).
-- ==========================================================================
CREATE TABLE IF NOT EXISTS hyperliquid_candles (
    id          BIGSERIAL       PRIMARY KEY,
    coin        TEXT            NOT NULL,
    interval    TEXT            NOT NULL,
    open_time   TIMESTAMPTZ     NOT NULL,
    close_time  TIMESTAMPTZ     NOT NULL,
    open        NUMERIC         NOT NULL,
    high        NUMERIC         NOT NULL,
    low         NUMERIC         NOT NULL,
    close       NUMERIC         NOT NULL,
    volume      NUMERIC         NOT NULL,
    num_trades  INT,
    created_at  TIMESTAMPTZ     DEFAULT NOW(),

    UNIQUE (coin, interval, open_time)
);

-- Primary query pattern: latest candles for a given coin + interval.
CREATE INDEX IF NOT EXISTS idx_candles_coin_interval
    ON hyperliquid_candles (coin, interval, close_time DESC);

-- ==========================================================================
-- Tick table: stores real-time partial candle updates and raw snapshots.
-- Uses a JSONB payload so the schema stays flexible as the upstream API
-- evolves.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS hyperliquid_ticks (
    id          BIGSERIAL       PRIMARY KEY,
    coin        TEXT            NOT NULL,
    received_at TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    payload     JSONB           NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ticks_coin_received
    ON hyperliquid_ticks (coin, received_at DESC);

-- Optional: enable Row-Level Security (RLS) so the anon key can only SELECT.
-- Uncomment if you want stricter access control.
--
-- ALTER TABLE hyperliquid_candles ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "anon_read_candles" ON hyperliquid_candles
--     FOR SELECT USING (true);
--
-- ALTER TABLE hyperliquid_ticks ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "anon_read_ticks" ON hyperliquid_ticks
--     FOR SELECT USING (true);
