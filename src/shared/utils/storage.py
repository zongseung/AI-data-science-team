"""Supabase storage service for persisting pipeline data."""

from datetime import datetime
from typing import Any

import structlog
from supabase import create_client, Client

from ai_data_science_team.config.settings import settings

logger = structlog.get_logger()


class StorageService:
    """Wrapper around Supabase for storing and retrieving pipeline data."""

    def __init__(self):
        self._client: Client | None = None
        self.log = logger.bind(component="storage")

    @property
    def client(self) -> Client:
        """Lazy-initialize Supabase client."""
        if self._client is None:
            if not settings.supabase_url or not settings.supabase_anon_key:
                raise RuntimeError(
                    "SUPABASE_URL and SUPABASE_ANON_KEY must be set"
                )
            self._client = create_client(
                settings.supabase_url, settings.supabase_anon_key
            )
        return self._client

    async def save_collection_result(
        self,
        stock_code: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Save collection results to Supabase."""
        record = {
            "stock_code": stock_code,
            "collected_at": datetime.now().isoformat(),
            "price_data": data.get("price_data"),
            "disclosures": data.get("disclosures"),
            "news": data.get("news"),
            "market_data": data.get("market_data"),
            "quality_report": data.get("quality_report"),
        }

        result = self.client.table("collections").insert(record).execute()
        self.log.info("saved_collection", stock_code=stock_code)
        return result.data[0] if result.data else {}

    async def save_analysis_result(
        self,
        stock_code: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Save analysis results."""
        record = {
            "stock_code": stock_code,
            "analyzed_at": datetime.now().isoformat(),
            "eda": data.get("eda"),
            "features": data.get("features"),
            "statistical": data.get("statistical"),
            "sentiment": data.get("sentiment"),
            "sector": data.get("sector"),
        }

        result = self.client.table("analyses").insert(record).execute()
        self.log.info("saved_analysis", stock_code=stock_code)
        return result.data[0] if result.data else {}

    async def save_forecast_result(
        self,
        stock_code: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Save forecast results."""
        record = {
            "stock_code": stock_code,
            "forecast_at": datetime.now().isoformat(),
            "ml_results": data.get("ml_results"),
            "backtest": data.get("backtest"),
            "risk": data.get("risk"),
        }

        result = self.client.table("forecasts").insert(record).execute()
        self.log.info("saved_forecast", stock_code=stock_code)
        return result.data[0] if result.data else {}

    async def save_report(
        self,
        stock_code: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Save generated reports."""
        record = {
            "stock_code": stock_code,
            "generated_at": datetime.now().isoformat(),
            "comprehensive": data.get("comprehensive"),
            "investment_memo": data.get("investment_memo"),
            "risk_note": data.get("risk_note"),
            "final": data.get("final"),
        }

        result = self.client.table("reports").insert(record).execute()
        self.log.info("saved_report", stock_code=stock_code)
        return result.data[0] if result.data else {}

    async def get_latest_collection(
        self, stock_code: str
    ) -> dict[str, Any] | None:
        """Get the most recent collection for a stock."""
        result = (
            self.client.table("collections")
            .select("*")
            .eq("stock_code", stock_code)
            .order("collected_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_latest_report(
        self, stock_code: str
    ) -> dict[str, Any] | None:
        """Get the most recent report for a stock."""
        result = (
            self.client.table("reports")
            .select("*")
            .eq("stock_code", stock_code)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Hyperliquid / Crypto methods
    # ------------------------------------------------------------------

    async def get_hyperliquid_candles(
        self,
        coin: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query the hyperliquid_candles table for recent candle data.

        Args:
            coin: Coin symbol (e.g. "BTC").
            interval: Candle interval (e.g. "1h", "1d").
            limit: Maximum number of rows to return (newest first).

        Returns:
            List of candle dicts ordered by timestamp descending.
        """
        try:
            result = (
                self.client.table("hyperliquid_candles")
                .select("*")
                .eq("coin", coin)
                .eq("interval", interval)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            self.log.info(
                "get_hyperliquid_candles",
                coin=coin,
                interval=interval,
                count=len(result.data) if result.data else 0,
            )
            return result.data or []
        except Exception as exc:
            self.log.error(
                "get_hyperliquid_candles_failed",
                coin=coin,
                error=str(exc),
            )
            return []

    async def get_latest_crypto_snapshot(
        self,
        coins: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Get the latest candle per coin as a price snapshot.

        Args:
            coins: List of coin symbols (e.g. ["BTC", "ETH"]).

        Returns:
            Dict mapping coin symbol to its latest candle data.
        """
        snapshot: dict[str, dict[str, Any]] = {}
        for coin in coins:
            try:
                result = (
                    self.client.table("hyperliquid_candles")
                    .select("*")
                    .eq("coin", coin)
                    .order("timestamp", desc=True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    snapshot[coin] = result.data[0]
            except Exception as exc:
                self.log.error(
                    "get_latest_crypto_snapshot_failed",
                    coin=coin,
                    error=str(exc),
                )
        return snapshot


# Global storage instance
storage = StorageService()
