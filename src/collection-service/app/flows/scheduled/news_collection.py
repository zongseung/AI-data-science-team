"""News collection: scrapes latest news every 30 minutes."""

from prefect import flow

from ai_data_science_team.collectors.news_collector import NewsCollector
from ai_data_science_team.config.constants import STOCK_CODES
from ai_data_science_team.config.prefect_config import TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus


@flow(name="news_collection", tags=TAGS["scheduled"] + TAGS["collection"])
async def news_collection(
    stock_names: list[str] | None = None,
    count_per_stock: int = 5,
):
    """Collect latest news for tracked stocks.

    Runs every 30 minutes. Collects fewer articles per stock than
    the full pipeline to stay within rate limits.
    """
    if stock_names is None:
        stock_names = list(STOCK_CODES.keys())[:10]

    collector = NewsCollector()
    results = {}

    for name in stock_names:
        result = await collector.collect(stock_name=name, count=count_per_stock)
        if result.get("articles"):
            results[name] = result

    await event_bus.emit(
        EventType.COLLECTION_COMPLETED,
        {
            "type": "news",
            "stocks_checked": len(results),
            "total_articles": sum(r.get("count", 0) for r in results.values()),
        },
        source="news_collection",
    )

    return results
