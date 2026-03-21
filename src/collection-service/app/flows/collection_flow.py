"""Collection flow: orchestrates 4 collectors in parallel with data quality check."""

import asyncio
from typing import Any

from prefect import flow, task

from ai_data_science_team.collectors.stock_price_collector import StockPriceCollector
from ai_data_science_team.collectors.disclosure_collector import DisclosureCollector
from ai_data_science_team.collectors.news_collector import NewsCollector
from ai_data_science_team.collectors.market_data_collector import MarketDataCollector
from ai_data_science_team.collectors.data_quality import DataQualityChecker
from ai_data_science_team.config.prefect_config import RETRIES, TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus


@task(
    name="collect_stock_prices",
    tags=TAGS["collection"],
    retries=RETRIES["collector"]["retries"],
    retry_delay_seconds=RETRIES["collector"]["retry_delay_seconds"],
)
async def collect_stock_prices(stock_code: str, days: int = 60) -> dict[str, Any]:
    """Collect stock price data from Naver Finance."""
    await event_bus.emit(
        EventType.COLLECTION_PROGRESS,
        {"step": "stock_prices", "status": "started", "stock_code": stock_code},
        source="stock_price_collector",
    )
    collector = StockPriceCollector()
    result = await collector.collect(stock_code=stock_code, days=days)
    await event_bus.emit(
        EventType.COLLECTION_PROGRESS,
        {"step": "stock_prices", "status": "completed", "stock_code": stock_code},
        source="stock_price_collector",
    )
    return result


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
    await event_bus.emit(
        EventType.COLLECTION_PROGRESS,
        {"step": "disclosures", "status": "started", "stock_code": stock_code},
        source="disclosure_collector",
    )
    collector = DisclosureCollector()
    result = await collector.collect(
        stock_code=stock_code, corp_code=corp_code, days=days
    )
    await event_bus.emit(
        EventType.COLLECTION_PROGRESS,
        {"step": "disclosures", "status": "completed", "stock_code": stock_code},
        source="disclosure_collector",
    )
    return result


@task(
    name="collect_news",
    tags=TAGS["collection"],
    retries=RETRIES["collector"]["retries"],
    retry_delay_seconds=RETRIES["collector"]["retry_delay_seconds"],
)
async def collect_news(stock_name: str, count: int = 20) -> dict[str, Any]:
    """Collect news articles from Naver News."""
    await event_bus.emit(
        EventType.COLLECTION_PROGRESS,
        {"step": "news", "status": "started", "stock_name": stock_name},
        source="news_collector",
    )
    collector = NewsCollector()
    result = await collector.collect(stock_name=stock_name, count=count)
    await event_bus.emit(
        EventType.COLLECTION_PROGRESS,
        {"step": "news", "status": "completed", "stock_name": stock_name},
        source="news_collector",
    )
    return result


@task(
    name="collect_market_data",
    tags=TAGS["collection"],
    retries=RETRIES["collector"]["retries"],
    retry_delay_seconds=RETRIES["collector"]["retry_delay_seconds"],
)
async def collect_market_data() -> dict[str, Any]:
    """Collect broad market data (KOSPI, exchange rate, treasury yield)."""
    await event_bus.emit(
        EventType.COLLECTION_PROGRESS,
        {"step": "market_data", "status": "started"},
        source="market_data_collector",
    )
    collector = MarketDataCollector()
    result = await collector.collect()
    await event_bus.emit(
        EventType.COLLECTION_PROGRESS,
        {"step": "market_data", "status": "completed"},
        source="market_data_collector",
    )
    return result


@task(name="check_data_quality", tags=TAGS["collection"])
async def check_data_quality(collected_data: dict[str, Any]) -> dict[str, Any]:
    """Run data quality checks on all collected data."""
    checker = DataQualityChecker()
    return checker.check(collected_data)


@flow(name="collection_flow", tags=TAGS["collection"])
async def collection_flow(
    stock_code: str,
    stock_name: str,
    corp_code: str,
) -> dict[str, Any]:
    """Main collection flow: runs 4 collectors in parallel, then quality check.

    Args:
        stock_code: Stock code (e.g., "005930")
        stock_name: Stock name in Korean (e.g., "삼성전자")
        corp_code: DART corporation code (e.g., "00126380")

    Returns:
        dict with price_data, disclosures, news, market_data, quality_report
    """
    await event_bus.emit(
        EventType.COLLECTION_STARTED,
        {"stock_code": stock_code, "stock_name": stock_name},
        source="collection_flow",
    )

    # Run 4 collectors in parallel
    price_future = collect_stock_prices.submit(stock_code)
    disclosure_future = collect_disclosures.submit(stock_code, corp_code)
    news_future = collect_news.submit(stock_name)
    market_future = collect_market_data.submit()

    price_data = await price_future.result()
    disclosure_data = await disclosure_future.result()
    news_data = await news_future.result()
    market_data = await market_future.result()

    # Assemble collected data
    collected_data = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "price_data": price_data,
        "disclosures": disclosure_data,
        "news": news_data,
        "market_data": market_data,
    }

    # Sequential: data quality check
    quality_report = await check_data_quality(collected_data)
    collected_data["quality_report"] = quality_report

    await event_bus.emit(
        EventType.COLLECTION_COMPLETED,
        {
            "stock_code": stock_code,
            "quality_status": quality_report["overall_status"],
        },
        source="collection_flow",
    )

    return collected_data
