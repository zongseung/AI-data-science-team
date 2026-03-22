"""Hyperliquid service entrypoint.

Starts the WebSocket candle collector as a background async task and exposes
a lightweight FastAPI app for health checks and readiness probes.

Usage::

    # Run directly
    python -m app.main

    # Or via uvicorn
    uvicorn app.main:app --host 0.0.0.0 --port 8090
"""

from __future__ import annotations

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .collector import HyperliquidCollector
from .config import hl_settings
from .sentiment_task import run_sentiment_analysis, sentiment_loop
from .storage import hl_storage

logger = structlog.get_logger()
log = logger.bind(component="hl_main")

_collector: HyperliquidCollector | None = None
_collector_task: asyncio.Task[None] | None = None
_sentiment_task: asyncio.Task[None] | None = None


# ------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage the collector and sentiment task lifecycles alongside the FastAPI app."""
    global _collector, _collector_task, _sentiment_task

    _collector = HyperliquidCollector()
    _collector_task = asyncio.create_task(
        _collector.start(), name="hl-collector"
    )
    log.info("collector_task_created")

    # Start sentiment analysis background loop (runs once on startup, then every 6h)
    _sentiment_task = asyncio.create_task(
        sentiment_loop(), name="hl-sentiment"
    )
    log.info("sentiment_task_created")

    yield  # app is running

    # Shutdown
    log.info("shutting_down")
    if _collector is not None:
        await _collector.stop()
    if _collector_task is not None:
        _collector_task.cancel()
        try:
            await _collector_task
        except asyncio.CancelledError:
            pass
    if _sentiment_task is not None:
        _sentiment_task.cancel()
        try:
            await _sentiment_task
        except asyncio.CancelledError:
            pass
    log.info("shutdown_complete")


# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------

app = FastAPI(
    title="Hyperliquid Collector Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/readiness")
async def readiness() -> dict[str, str | bool]:
    """Readiness probe -- checks whether the collector is running."""
    running = (
        _collector_task is not None
        and not _collector_task.done()
    )
    return {"status": "ready" if running else "not_ready", "collector_running": running}


@app.get("/config")
async def config_view() -> dict[str, object]:
    """Return the active (non-secret) configuration."""
    return {
        "ws_url": hl_settings.ws_url,
        "coins": hl_settings.coins,
        "intervals": hl_settings.intervals,
        "heartbeat_interval_seconds": hl_settings.heartbeat_interval_seconds,
    }


# ------------------------------------------------------------------
# Sentiment API endpoints
# ------------------------------------------------------------------


@app.get("/api/sentiment/{coin}")
async def get_sentiment(coin: str, limit: int = 10) -> dict[str, object]:
    """Get latest sentiment data for a coin.

    Parameters
    ----------
    coin:
        Coin ticker (e.g. BTC, ETH, SOL).
    limit:
        Maximum number of recent articles to return.
    """
    try:
        client = hl_storage.client
        result = (
            client.table("crypto_news")
            .select("*")
            .eq("coin", coin.upper())
            .order("collected_at", desc=True)
            .limit(limit)
            .execute()
        )
        articles = result.data if result.data else []

        # Also fetch latest summary
        summary_result = (
            client.table("crypto_sentiment_summary")
            .select("*")
            .eq("coin", coin.upper())
            .order("period_start", desc=True)
            .limit(1)
            .execute()
        )
        summary = summary_result.data[0] if summary_result.data else None

        return {
            "coin": coin.upper(),
            "articles": articles,
            "summary": summary,
        }
    except Exception as exc:
        log.error("sentiment_query_error", coin=coin, error=str(exc))
        return {"coin": coin.upper(), "articles": [], "summary": None, "error": str(exc)}


@app.get("/api/sentiment/summary/all")
async def get_sentiment_summary() -> dict[str, object]:
    """Get latest sentiment summary for all tracked coins."""
    try:
        client = hl_storage.client
        result = (
            client.table("crypto_sentiment_summary")
            .select("*")
            .order("period_start", desc=True)
            .limit(50)
            .execute()
        )
        summaries = result.data if result.data else []

        # Deduplicate: keep only the latest summary per coin
        latest: dict[str, dict] = {}
        for s in summaries:
            coin = s.get("coin", "")
            if coin not in latest:
                latest[coin] = s

        return {
            "summaries": list(latest.values()),
            "coins": list(latest.keys()),
        }
    except Exception as exc:
        log.error("summary_query_error", error=str(exc))
        return {"summaries": [], "coins": [], "error": str(exc)}


@app.post("/api/sentiment/run")
async def trigger_sentiment_analysis() -> dict[str, object]:
    """Manually trigger a sentiment analysis run."""
    try:
        result = await run_sentiment_analysis()
        return {"status": "completed", **result}
    except Exception as exc:
        log.error("manual_sentiment_run_error", error=str(exc))
        return {"status": "error", "error": str(exc)}


# ------------------------------------------------------------------
# Technical Indicators API
# ------------------------------------------------------------------


@app.get("/api/indicators/{coin}")
async def get_indicators(coin: str, interval: str = "15m", limit: int = 200) -> dict[str, object]:
    """Compute technical indicators for a coin from Supabase candle data.

    Returns SMA, EMA, RSI, MACD, Bollinger Bands, ATR, OBV, volatility.
    """
    from indicators.technical import compute_all
    import json
    import urllib.request
    import time

    candles: list = []

    # Try Supabase first
    try:
        client = hl_storage.client
        result = (
            client.table("hyperliquid_candles")
            .select("open,high,low,close,volume")
            .eq("coin", coin.upper())
            .eq("interval", interval)
            .order("close_time", desc=True)
            .limit(limit)
            .execute()
        )
        candles = result.data if result.data else []
    except Exception:
        pass  # fallback below

    # Fallback: Hyperliquid REST API
    if not candles:
        try:
            now = int(time.time() * 1000)
            ms_map = {"1m": 60000, "5m": 300000, "15m": 900000, "1h": 3600000}
            ms = ms_map.get(interval, 900000)
            body = json.dumps({
                "type": "candleSnapshot",
                "req": {"coin": coin.upper(), "interval": interval, "startTime": now - ms * limit, "endTime": now},
            }).encode()
            req = urllib.request.Request(
                "https://api.hyperliquid.xyz/info",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            candles = json.loads(resp.read())
        except Exception as exc:
            log.error("indicators_fetch_error", coin=coin, error=str(exc))
            return {"coin": coin.upper(), "error": str(exc)}

    # Reverse so oldest first
    if candles:
        candles.reverse()

    try:
        indicators = compute_all(candles)
        return {"coin": coin.upper(), "interval": interval, **indicators}
    except Exception as exc:
        log.error("indicators_compute_error", coin=coin, error=str(exc))
        return {"coin": coin.upper(), "error": str(exc)}


@app.get("/api/indicators/all/{interval}")
async def get_all_indicators(interval: str = "15m") -> dict[str, object]:
    """Compute indicators for all tracked coins."""
    coins = list(set(hl_settings.coins + ["HYPE"]))
    results = {}
    for coin in coins:
        try:
            data = await get_indicators(coin, interval)
            results[coin] = data
        except Exception as exc:
            results[coin] = {"error": str(exc)}
    return {"interval": interval, "coins": results}


# ------------------------------------------------------------------
# Direct execution
# ------------------------------------------------------------------


def _handle_signal(sig: signal.Signals) -> None:
    """Request graceful shutdown on SIGINT / SIGTERM."""
    log.info("signal_received", signal=sig.name)
    raise SystemExit(0)


def main() -> None:
    """Run the service."""
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    uvicorn.run(
        app,
        host=hl_settings.host,
        port=hl_settings.port,
        loop="asyncio",
        log_level="info",
    )


if __name__ == "__main__":
    main()
