"""Daily pipeline: runs full pipeline for all tracked stocks at 16:00 KST."""

from prefect import flow

from ai_data_science_team.config.constants import STOCK_CODES
from ai_data_science_team.config.prefect_config import TAGS
from ai_data_science_team.flows.master_flow import master_flow


@flow(name="daily_pipeline", tags=TAGS["scheduled"])
async def daily_pipeline(stock_names: list[str] | None = None):
    """Run full pipeline for specified stocks (defaults to all tracked stocks).

    Triggered daily at 16:00 KST on weekdays.
    """
    if stock_names is None:
        stock_names = list(STOCK_CODES.keys())

    results = {}
    for name in stock_names:
        stock_info = STOCK_CODES.get(name)
        if not stock_info:
            continue

        result = await master_flow(
            stock_code=stock_info["stock_code"],
            stock_name=name,
            corp_code=stock_info["corp_code"],
        )
        results[name] = result

    return results
