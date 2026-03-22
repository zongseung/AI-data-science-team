"""Hyperliquid service configuration.

Extends the shared settings with service-specific WebSocket and subscription
parameters.  All values can be overridden via environment variables prefixed
with ``HYPERLIQUID_``.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class HyperliquidSettings(BaseSettings):
    """Settings for the Hyperliquid real-time candle collector."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "HYPERLIQUID_",
    }

    # WebSocket
    ws_url: str = Field(
        default="wss://api.hyperliquid.xyz/ws",
        description="Hyperliquid WebSocket endpoint",
    )

    # Subscriptions
    coins: list[str] = Field(
        default=["BTC", "ETH", "SOL"],
        description="Coins to subscribe for candle data",
    )
    intervals: list[str] = Field(
        default=["15m"],
        description="Candle intervals to subscribe (e.g. 1m, 5m, 15m, 1h)",
    )

    # Connection tuning
    heartbeat_interval_seconds: int = Field(
        default=50,
        description="Seconds between WebSocket ping frames",
    )
    reconnect_base_delay: float = Field(
        default=1.0,
        description="Initial delay (seconds) before reconnect attempt",
    )
    reconnect_max_delay: float = Field(
        default=60.0,
        description="Maximum reconnect backoff delay (seconds)",
    )

    # Supabase (read from shared env vars without prefix override)
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")

    # FastAPI health server
    host: str = Field(default="0.0.0.0", description="Health-check server bind host")
    port: int = Field(default=8090, description="Health-check server bind port")


hl_settings = HyperliquidSettings()
