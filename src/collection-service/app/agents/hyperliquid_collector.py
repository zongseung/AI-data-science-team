"""Hyperliquid data reader.

This is NOT a WebSocket collector -- the WS service already writes candle data
to Supabase.  This module reads that data back and, if the stored data is stale,
falls back to Hyperliquid's public REST API.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog

from src.shared.utils.storage import storage

logger = structlog.get_logger()

# Hyperliquid public REST endpoint (no auth required)
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"

# If the most recent candle is older than this, consider data stale
STALENESS_THRESHOLD = timedelta(minutes=10)


class HyperliquidCollector:
    """Read candle / snapshot data that the WS service stored in Supabase.

    Falls back to the Hyperliquid REST API when Supabase data is stale or
    unavailable.
    """

    def __init__(self) -> None:
        self.log = logger.bind(component="hyperliquid_collector")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_latest_candles(
        self,
        coin: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return recent candles for *coin*.

        Tries Supabase first; falls back to REST if stale.
        """
        candles = await storage.get_hyperliquid_candles(
            coin=coin,
            interval=interval,
            limit=limit,
        )

        if candles and not self._is_stale(candles):
            self.log.info(
                "candles_from_supabase",
                coin=coin,
                interval=interval,
                count=len(candles),
            )
            return candles

        self.log.info(
            "candles_stale_or_missing_fallback_to_rest",
            coin=coin,
            interval=interval,
        )
        return await self._fetch_candles_rest(coin, interval, limit)

    async def get_price_snapshot(
        self,
        coins: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Return the latest candle per coin as a price snapshot.

        Keys are coin symbols, values contain open/high/low/close/volume.
        """
        snapshot = await storage.get_latest_crypto_snapshot(coins)

        # Fill in missing coins via REST
        missing = [c for c in coins if c not in snapshot]
        if missing:
            self.log.info("snapshot_missing_coins_fallback", missing=missing)
            for coin in missing:
                candles = await self._fetch_candles_rest(coin, "1h", 1)
                if candles:
                    snapshot[coin] = candles[0]

        return snapshot

    # ------------------------------------------------------------------
    # REST fallback
    # ------------------------------------------------------------------

    async def _fetch_candles_rest(
        self,
        coin: str,
        interval: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch candle data directly from Hyperliquid REST API."""
        interval_ms_map: dict[str, int] = {
            "1m": 60_000,
            "5m": 300_000,
            "15m": 900_000,
            "1h": 3_600_000,
            "4h": 14_400_000,
            "1d": 86_400_000,
        }

        interval_ms = interval_ms_map.get(interval, 3_600_000)
        now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        start_ms = now_ms - interval_ms * limit

        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_ms,
                "endTime": now_ms,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(HYPERLIQUID_INFO_URL, json=payload)
                resp.raise_for_status()
                raw = resp.json()

            candles = [
                {
                    "coin": coin,
                    "timestamp": c.get("t"),
                    "open": float(c.get("o", 0)),
                    "high": float(c.get("h", 0)),
                    "low": float(c.get("l", 0)),
                    "close": float(c.get("c", 0)),
                    "volume": float(c.get("v", 0)),
                    "interval": interval,
                }
                for c in raw
            ]
            self.log.info(
                "candles_from_rest",
                coin=coin,
                interval=interval,
                count=len(candles),
            )
            return candles

        except Exception as exc:
            self.log.error(
                "rest_candle_fetch_failed",
                coin=coin,
                error=str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_stale(candles: list[dict[str, Any]]) -> bool:
        """Check whether the newest candle is older than the staleness threshold."""
        if not candles:
            return True

        latest = candles[0]  # Supabase returns newest-first
        ts_raw = latest.get("timestamp") or latest.get("t")
        if ts_raw is None:
            return True

        try:
            if isinstance(ts_raw, (int, float)):
                # Epoch milliseconds
                latest_dt = datetime.fromtimestamp(ts_raw / 1000, tz=timezone.utc)
            else:
                latest_dt = datetime.fromisoformat(str(ts_raw))
                if latest_dt.tzinfo is None:
                    latest_dt = latest_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return True

        return datetime.now(tz=timezone.utc) - latest_dt > STALENESS_THRESHOLD
