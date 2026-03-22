"""Intraday check: fetches current prices every 10 minutes during market hours."""

from prefect import flow, task

from ai_data_science_team.collectors.stock_price_collector import StockPriceCollector
from ai_data_science_team.config.constants import STOCK_CODES
from ai_data_science_team.config.prefect_config import TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus


@task(name="fetch_intraday_price", tags=TAGS["collection"])
async def fetch_intraday_price(stock_code: str, stock_name: str) -> dict:
    """Fetch current price for a single stock."""
    from playwright.async_api import async_playwright

    collector = StockPriceCollector()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(10_000)
        try:
            result = await collector._fetch_current_price(page, stock_code)
            result["stock_name"] = stock_name
            return result
        finally:
            await browser.close()


@flow(name="intraday_check", tags=TAGS["scheduled"] + TAGS["collection"])
async def intraday_check(stock_names: list[str] | None = None):
    """Check current prices for tracked stocks during market hours.

    Runs every 10 minutes from 09:00-15:00 KST on weekdays.
    """
    if stock_names is None:
        # Default: check top 5 stocks for intraday
        stock_names = list(STOCK_CODES.keys())[:5]

    results = {}
    for name in stock_names:
        stock_info = STOCK_CODES.get(name)
        if not stock_info:
            continue

        price = await fetch_intraday_price(
            stock_info["stock_code"], name
        )
        results[name] = price

    await event_bus.emit(
        EventType.COLLECTION_COMPLETED,
        {"type": "intraday", "stocks_checked": len(results)},
        source="intraday_check",
    )

    return results
