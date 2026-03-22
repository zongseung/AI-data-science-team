"""Hyperliquid WebSocket candle collector.

Connects to ``wss://api.hyperliquid.xyz/ws``, subscribes to candle channels
for the configured coins/intervals, and persists closed candles to Supabase.

Key behaviours:
* Async-first -- uses the ``websockets`` library.
* Sends a ping frame every ``heartbeat_interval_seconds``.
* Reconnects with exponential backoff on any disconnection.
* Publishes ``CANDLE_CLOSED`` events to the in-process event bus.
"""

from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timezone
from typing import Any

import structlog
import websockets
from websockets.asyncio.client import ClientConnection

from .config import hl_settings
from .storage import hl_storage

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Optional event-bus integration.  The import may fail when the shared package
# is not on ``sys.path`` (e.g. running the service in isolation), so we
# degrade gracefully.
# ---------------------------------------------------------------------------
try:
    from src.shared.utils.event_bus import EventType, event_bus  # type: ignore[import-untyped]

    _HAS_EVENT_BUS = True
except ImportError:
    _HAS_EVENT_BUS = False
    event_bus = None  # type: ignore[assignment]


class HyperliquidCollector:
    """Real-time candle collector over Hyperliquid's public WebSocket API."""

    def __init__(
        self,
        coins: list[str] | None = None,
        intervals: list[str] | None = None,
    ) -> None:
        self.coins = coins or hl_settings.coins
        self.intervals = intervals or hl_settings.intervals
        self.ws_url = hl_settings.ws_url

        self._ws: ClientConnection | None = None
        self._running = False
        self._reconnect_attempt = 0
        self._last_candles: dict[tuple[str, str], dict[str, Any]] = {}

        self.log = logger.bind(component="hl_collector")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect and begin streaming.  Blocks until ``stop()`` is called."""
        self._running = True
        self.log.info(
            "collector_starting",
            coins=self.coins,
            intervals=self.intervals,
            ws_url=self.ws_url,
        )

        while self._running:
            try:
                await self._connect_and_stream()
            except (
                websockets.ConnectionClosed,
                websockets.InvalidURI,
                websockets.InvalidHandshake,
                OSError,
            ) as exc:
                if not self._running:
                    break
                delay = self._backoff_delay()
                self.log.warning(
                    "ws_disconnected",
                    error=str(exc),
                    reconnect_in=delay,
                    attempt=self._reconnect_attempt,
                )
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                self.log.info("collector_cancelled")
                break
            except Exception:
                if not self._running:
                    break
                delay = self._backoff_delay()
                self.log.exception(
                    "ws_unexpected_error",
                    reconnect_in=delay,
                    attempt=self._reconnect_attempt,
                )
                await asyncio.sleep(delay)

    async def stop(self) -> None:
        """Gracefully shut down the collector."""
        self._running = False
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        self.log.info("collector_stopped")

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def _connect_and_stream(self) -> None:
        """Open a WebSocket, subscribe, and process messages."""
        async with websockets.connect(
            self.ws_url,
            ping_interval=None,  # we manage our own heartbeat
            close_timeout=10,
        ) as ws:
            self._ws = ws
            self._reconnect_attempt = 0
            self.log.info("ws_connected", url=self.ws_url)

            await self._subscribe_all(ws)

            # Run message reader and heartbeat concurrently.
            reader_task = asyncio.create_task(self._read_loop(ws))
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))

            try:
                done, pending = await asyncio.wait(
                    [reader_task, heartbeat_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                # Cancel the surviving task.
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                # Re-raise if the completed task had an exception.
                for task in done:
                    task.result()
            finally:
                self._ws = None

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    async def _subscribe_all(self, ws: ClientConnection) -> None:
        """Send subscription messages for every coin/interval pair."""
        for coin in self.coins:
            for interval in self.intervals:
                msg = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "candle",
                        "coin": coin,
                        "interval": interval,
                    },
                }
                await ws.send(json.dumps(msg))
                self.log.info(
                    "subscribed",
                    coin=coin,
                    interval=interval,
                )

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------

    async def _read_loop(self, ws: ClientConnection) -> None:
        """Continuously read and dispatch incoming messages."""
        async for raw in ws:
            if not self._running:
                break
            try:
                payload = json.loads(raw)
                await self._handle_message(payload)
            except json.JSONDecodeError:
                self.log.warning("ws_invalid_json", raw=raw[:200])
            except Exception:
                self.log.exception("ws_handle_error")

    async def _handle_message(self, payload: dict[str, Any]) -> None:
        """Route a parsed WebSocket message to the appropriate handler."""
        channel = payload.get("channel")
        data = payload.get("data")

        if channel == "candle":
            await self._on_candle(data)
        elif channel == "subscriptionResponse":
            self.log.debug("subscription_ack", data=data)
        elif channel == "pong" or payload.get("method") == "pong":
            pass  # heartbeat response
        elif channel == "error":
            self.log.error("ws_server_error", data=data)
        else:
            self.log.debug("ws_unknown_channel", channel=channel, data=data)

    async def _on_candle(self, data: dict[str, Any]) -> None:
        """Process an incoming candle message.

        Hyperliquid sends a single candle object per message with keys:
        s (coin), i (interval), t (open_time), T (close_time), o, h, l, c, v, n.

        We detect candle close by tracking open_time: when a new open_time
        arrives, the previous candle is confirmed closed.
        """
        if data is None:
            return

        coin: str = data.get("s", "")
        interval: str = data.get("i", "")
        candle = self._parse_candle(data)
        key = (coin, interval)

        prev = self._last_candles.get(key)

        if prev is not None and prev["open_time"] != candle["open_time"]:
            # Previous candle is now closed — persist it
            await hl_storage.save_candle(coin, interval, prev)
            await self._emit_candle_event(coin, interval, prev)
            self.log.info(
                "candle_closed",
                coin=coin,
                interval=interval,
                close=prev["close"],
                volume=prev["volume"],
            )

        # Always update latest candle
        self._last_candles[key] = candle

    @staticmethod
    def _parse_candle(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalise a raw Hyperliquid candle dict into our schema."""
        open_ts = raw.get("t", raw.get("T", 0))
        close_ts = raw.get("T", open_ts)

        return {
            "open_time": datetime.fromtimestamp(
                open_ts / 1000, tz=timezone.utc
            ).isoformat(),
            "close_time": datetime.fromtimestamp(
                close_ts / 1000, tz=timezone.utc
            ).isoformat(),
            "open": float(raw.get("o", 0)),
            "high": float(raw.get("h", 0)),
            "low": float(raw.get("l", 0)),
            "close": float(raw.get("c", 0)),
            "volume": float(raw.get("v", 0)),
            "num_trades": int(raw.get("n", 0)) if raw.get("n") else None,
        }

    # ------------------------------------------------------------------
    # Event bus integration
    # ------------------------------------------------------------------

    async def _emit_candle_event(
        self,
        coin: str,
        interval: str,
        candle: dict[str, Any],
    ) -> None:
        """Publish a candle-closed event on the shared event bus."""
        if not _HAS_EVENT_BUS or event_bus is None:
            return
        try:
            await event_bus.emit(
                event_type=EventType.COLLECTION_COMPLETED,
                data={
                    "source": "hyperliquid",
                    "coin": coin,
                    "interval": interval,
                    "candle": candle,
                },
                source="hyperliquid-collector",
            )
        except Exception:
            self.log.warning("event_bus_emit_failed", exc_info=True)

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self, ws: ClientConnection) -> None:
        """Send periodic text-based ping to keep the connection alive.

        Hyperliquid expects ``{"method": "ping"}`` as a text message,
        not a WebSocket ping frame.
        """
        interval = hl_settings.heartbeat_interval_seconds
        while self._running:
            await asyncio.sleep(interval)
            try:
                await ws.send(json.dumps({"method": "ping"}))
                self.log.debug("heartbeat_ok")
            except Exception:
                self.log.warning("heartbeat_failed")
                raise

    # ------------------------------------------------------------------
    # Backoff
    # ------------------------------------------------------------------

    def _backoff_delay(self) -> float:
        """Compute exponential backoff delay with jitter."""
        self._reconnect_attempt += 1
        delay = min(
            hl_settings.reconnect_base_delay * math.pow(2, self._reconnect_attempt - 1),
            hl_settings.reconnect_max_delay,
        )
        return delay
