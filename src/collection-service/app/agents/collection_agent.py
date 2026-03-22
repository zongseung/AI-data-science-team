"""Collection Agent: unified entry point for KRX + Hyperliquid data collection.

Accepts a ``source`` parameter ("krx", "hyperliquid", or "all") and delegates
to the appropriate collectors / readers.
"""

import asyncio
from typing import Any, Literal

from prefect import task

from src.shared.agents.base_agent import AgentResult, AgentStatus, BaseAgent
from src.collection_service.app.agents.hyperliquid_collector import HyperliquidCollector
from ai_data_science_team.collectors.stock_price_collector import StockPriceCollector
from ai_data_science_team.collectors.disclosure_collector import DisclosureCollector
from ai_data_science_team.collectors.news_collector import NewsCollector
from ai_data_science_team.collectors.market_data_collector import MarketDataCollector
from ai_data_science_team.collectors.data_quality import DataQualityChecker
from src.shared.config.constants import CRYPTO_COINS
from ai_data_science_team.config.prefect_config import RETRIES, TAGS
from src.shared.utils.event_bus import EventType


SourceType = Literal["krx", "hyperliquid", "all"]


# ---------------------------------------------------------------
# Prefect tasks (kept at module level so Prefect can track them)
# ---------------------------------------------------------------

@task(
    name="collect_stock_prices",
    tags=TAGS["collection"],
    retries=RETRIES["collector"]["retries"],
    retry_delay_seconds=RETRIES["collector"]["retry_delay_seconds"],
)
async def collect_stock_prices(stock_code: str, days: int = 60) -> dict[str, Any]:
    """Collect stock price data from Naver Finance."""
    collector = StockPriceCollector()
    return await collector.collect(stock_code=stock_code, days=days)


@task(
    name="collect_disclosures",
    tags=TAGS["collection"],
    retries=RETRIES["collector"]["retries"],
    retry_delay_seconds=RETRIES["collector"]["retry_delay_seconds"],
)
async def collect_disclosures(
    stock_code: str, corp_code: str, days: int = 30
) -> dict[str, Any]:
    """Collect disclosure data from DART OpenAPI."""
    collector = DisclosureCollector()
    return await collector.collect(
        stock_code=stock_code, corp_code=corp_code, days=days
    )


@task(
    name="collect_news",
    tags=TAGS["collection"],
    retries=RETRIES["collector"]["retries"],
    retry_delay_seconds=RETRIES["collector"]["retry_delay_seconds"],
)
async def collect_news(stock_name: str, count: int = 20) -> dict[str, Any]:
    """Collect news articles from Naver News."""
    collector = NewsCollector()
    return await collector.collect(stock_name=stock_name, count=count)


@task(
    name="collect_market_data",
    tags=TAGS["collection"],
    retries=RETRIES["collector"]["retries"],
    retry_delay_seconds=RETRIES["collector"]["retry_delay_seconds"],
)
async def collect_market_data() -> dict[str, Any]:
    """Collect broad market data (KOSPI, exchange rate, treasury yield)."""
    collector = MarketDataCollector()
    return await collector.collect()


@task(name="collect_hyperliquid_data", tags=TAGS["collection"])
async def collect_hyperliquid_data(
    coins: list[str] | None = None,
    interval: str = "1h",
    limit: int = 100,
) -> dict[str, Any]:
    """Fetch Hyperliquid candle data (from Supabase or REST fallback)."""
    hl = HyperliquidCollector()
    target_coins = coins or list(CRYPTO_COINS.keys())

    candles: dict[str, list[dict[str, Any]]] = {}
    for coin in target_coins:
        candles[coin] = await hl.get_latest_candles(coin, interval, limit)

    snapshot = await hl.get_price_snapshot(target_coins)

    return {
        "candles": candles,
        "snapshot": snapshot,
        "coins": target_coins,
        "interval": interval,
    }


@task(name="check_data_quality", tags=TAGS["collection"])
async def check_data_quality(collected_data: dict[str, Any]) -> dict[str, Any]:
    """Run data quality checks on collected data."""
    checker = DataQualityChecker()
    return checker.check(collected_data)


# ---------------------------------------------------------------
# Collection Agent
# ---------------------------------------------------------------

class CollectionAgent(BaseAgent):
    """Unified collection agent for KRX and Hyperliquid data sources."""

    def __init__(self) -> None:
        super().__init__(
            name="collection_agent",
            role="Data collection across KRX and Hyperliquid markets",
        )

    @property
    def data_sources(self) -> list[str]:
        return ["krx", "hyperliquid"]

    async def execute(
        self,
        *,
        source: SourceType = "all",
        # KRX parameters
        stock_code: str = "",
        stock_name: str = "",
        corp_code: str = "",
        # Hyperliquid parameters
        coins: list[str] | None = None,
        interval: str = "1h",
        candle_limit: int = 100,
        **kwargs: Any,
    ) -> AgentResult:
        """Run data collection for the requested source(s).

        Args:
            source: "krx", "hyperliquid", or "all".
            stock_code: KRX stock code (required when source includes krx).
            stock_name: KRX stock name in Korean.
            corp_code: DART corporation code.
            coins: Crypto coin symbols for Hyperliquid.
            interval: Candle interval for Hyperliquid.
            candle_limit: Number of candles to fetch.

        Returns:
            AgentResult with source-tagged data.
        """
        self.log.info("execute_start", source=source)
        await self.emit(
            EventType.COLLECTION_STARTED,
            {"source": source, "stock_code": stock_code, "coins": coins},
        )

        errors: list[str] = []
        data: dict[str, Any] = {"source": source}
        tasks: list[tuple[str, Any]] = []

        # ---- Build task list based on source ----
        if source in ("krx", "all"):
            if not stock_code:
                errors.append("stock_code is required for KRX collection")
            else:
                tasks.append(("krx", self._collect_krx(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    corp_code=corp_code,
                )))

        if source in ("hyperliquid", "all"):
            tasks.append(("hyperliquid", self._collect_hyperliquid(
                coins=coins,
                interval=interval,
                limit=candle_limit,
            )))

        # ---- Run tasks concurrently ----
        if tasks:
            results = await asyncio.gather(
                *(coro for _, coro in tasks),
                return_exceptions=True,
            )

            for (label, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    error_msg = f"{label}: {result}"
                    errors.append(error_msg)
                    self.log.error("source_failed", source=label, error=str(result))
                else:
                    data[label] = result

        # ---- Determine status ----
        if errors and not any(k in data for k in ("krx", "hyperliquid")):
            status = AgentStatus.FAILED
        elif errors:
            status = AgentStatus.PARTIAL
        else:
            status = AgentStatus.SUCCESS

        metadata = {
            "source": source,
            "stock_code": stock_code,
            "coins": coins or list(CRYPTO_COINS.keys()),
        }

        await self.emit(
            EventType.COLLECTION_COMPLETED,
            {"source": source, "status": status.value, "errors": errors},
        )

        self.log.info("execute_done", status=status.value, errors=errors)
        return AgentResult(
            status=status.value,
            data=data,
            errors=errors,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _collect_krx(
        self,
        stock_code: str,
        stock_name: str,
        corp_code: str,
    ) -> dict[str, Any]:
        """Run the 4 KRX collectors in parallel, then quality check."""
        await self.emit(
            EventType.COLLECTION_PROGRESS,
            {"step": "krx", "status": "started", "stock_code": stock_code},
        )

        # Submit all 4 in parallel via Prefect tasks
        price_future = collect_stock_prices.submit(stock_code)
        disclosure_future = collect_disclosures.submit(stock_code, corp_code)
        news_future = collect_news.submit(stock_name)
        market_future = collect_market_data.submit()

        price_data = await price_future.result()
        disclosure_data = await disclosure_future.result()
        news_data = await news_future.result()
        market_data = await market_future.result()

        collected = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "price_data": price_data,
            "disclosures": disclosure_data,
            "news": news_data,
            "market_data": market_data,
        }

        # Data quality check
        quality_report = await check_data_quality(collected)
        collected["quality_report"] = quality_report

        await self.emit(
            EventType.COLLECTION_PROGRESS,
            {
                "step": "krx",
                "status": "completed",
                "stock_code": stock_code,
                "quality_status": quality_report.get("overall_status"),
            },
        )

        return collected

    async def _collect_hyperliquid(
        self,
        coins: list[str] | None,
        interval: str,
        limit: int,
    ) -> dict[str, Any]:
        """Fetch Hyperliquid candle data via Prefect task."""
        await self.emit(
            EventType.COLLECTION_PROGRESS,
            {"step": "hyperliquid", "status": "started", "coins": coins},
        )

        result = await collect_hyperliquid_data(
            coins=coins,
            interval=interval,
            limit=limit,
        )

        await self.emit(
            EventType.COLLECTION_PROGRESS,
            {
                "step": "hyperliquid",
                "status": "completed",
                "coins": result.get("coins"),
            },
        )

        return result
