"""Supabase storage layer for Hyperliquid candle and tick data.

Follows the same lazy-initialisation pattern used by the shared
``StorageService`` but is scoped to the ``hyperliquid_candles`` table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from supabase import Client, create_client

from .config import hl_settings

logger = structlog.get_logger()


class HyperliquidStorage:
    """Supabase wrapper for the ``hyperliquid_candles`` table."""

    TABLE_CANDLES = "hyperliquid_candles"
    TABLE_TICKS = "hyperliquid_ticks"

    def __init__(self) -> None:
        self._client: Client | None = None
        self.log = logger.bind(component="hl_storage")

    @property
    def client(self) -> Client:
        """Lazy-initialise the Supabase client."""
        if self._client is None:
            url = hl_settings.supabase_url
            key = hl_settings.supabase_anon_key
            if not url or not key:
                raise RuntimeError(
                    "SUPABASE_URL and SUPABASE_ANON_KEY must be set"
                )
            self._client = create_client(url, key)
        return self._client

    # ------------------------------------------------------------------
    # Candle persistence
    # ------------------------------------------------------------------

    async def save_candle(
        self,
        coin: str,
        interval: str,
        candle_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Upsert a single closed candle into Supabase.

        ``candle_data`` is expected to contain at least:
            open_time, close_time, open, high, low, close, volume
        Optional: num_trades
        """
        record = {
            "coin": coin,
            "interval": interval,
            "open_time": candle_data["open_time"],
            "close_time": candle_data["close_time"],
            "open": str(candle_data["open"]),
            "high": str(candle_data["high"]),
            "low": str(candle_data["low"]),
            "close": str(candle_data["close"]),
            "volume": str(candle_data["volume"]),
            "num_trades": candle_data.get("num_trades"),
            "created_at": datetime.utcnow().isoformat(),
        }

        # Upsert on the UNIQUE(coin, interval, open_time) constraint.
        result = (
            self.client.table(self.TABLE_CANDLES)
            .upsert(record, on_conflict="coin,interval,open_time")
            .execute()
        )
        self.log.info(
            "candle_saved",
            coin=coin,
            interval=interval,
            open_time=candle_data["open_time"],
        )
        return result.data[0] if result.data else {}

    async def get_candles(
        self,
        coin: str,
        interval: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return the most recent *limit* candles for *coin*/*interval*."""
        result = (
            self.client.table(self.TABLE_CANDLES)
            .select("*")
            .eq("coin", coin)
            .eq("interval", interval)
            .order("close_time", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data if result.data else []

    # ------------------------------------------------------------------
    # Tick / real-time update persistence
    # ------------------------------------------------------------------

    async def save_tick(
        self,
        coin: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist a real-time tick / partial candle update.

        This is intentionally lightweight -- the table schema is flexible
        (JSONB ``payload`` column) so callers can store arbitrary snapshots.
        """
        record = {
            "coin": coin,
            "received_at": datetime.utcnow().isoformat(),
            "payload": data,
        }
        result = (
            self.client.table(self.TABLE_TICKS)
            .insert(record)
            .execute()
        )
        self.log.debug("tick_saved", coin=coin)
        return result.data[0] if result.data else {}


# Global singleton
hl_storage = HyperliquidStorage()
