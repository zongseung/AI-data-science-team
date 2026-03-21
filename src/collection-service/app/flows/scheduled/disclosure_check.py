"""Disclosure check: polls DART API for new disclosures every hour."""

from prefect import flow

from ai_data_science_team.collectors.disclosure_collector import DisclosureCollector
from ai_data_science_team.config.constants import STOCK_CODES
from ai_data_science_team.config.prefect_config import TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus


@flow(name="disclosure_check", tags=TAGS["scheduled"] + TAGS["collection"])
async def disclosure_check(stock_names: list[str] | None = None):
    """Check for new disclosures on DART for tracked stocks.

    Runs every hour. Only fetches disclosures from the last 1 day
    to minimize API calls.
    """
    if stock_names is None:
        stock_names = list(STOCK_CODES.keys())

    collector = DisclosureCollector()
    results = {}

    for name in stock_names:
        stock_info = STOCK_CODES.get(name)
        if not stock_info:
            continue

        result = await collector.collect(
            stock_code=stock_info["stock_code"],
            corp_code=stock_info["corp_code"],
            days=1,
        )

        if result.get("disclosures"):
            results[name] = result
            await event_bus.emit(
                EventType.COLLECTION_COMPLETED,
                {
                    "type": "disclosure",
                    "stock_name": name,
                    "count": len(result["disclosures"]),
                },
                source="disclosure_check",
            )

    return results
