"""Collection flow: orchestrates data collection via the CollectionAgent.

Supports multiple data sources through the ``source`` parameter:
- "krx" (default): runs 4 KRX collectors in parallel + quality check
- "hyperliquid": fetches crypto candle data from Supabase / REST
- "all": runs both in parallel
"""

from typing import Any, Literal

from prefect import flow

from src.collection_service.app.agents.collection_agent import CollectionAgent
from ai_data_science_team.config.prefect_config import TAGS
from src.shared.utils.event_bus import EventType, event_bus


@flow(name="collection_flow", tags=TAGS["collection"])
async def collection_flow(
    stock_code: str = "",
    stock_name: str = "",
    corp_code: str = "",
    source: Literal["krx", "hyperliquid", "all"] = "krx",
    coins: list[str] | None = None,
    interval: str = "1h",
    candle_limit: int = 100,
) -> dict[str, Any]:
    """Main collection flow delegating to CollectionAgent.

    Args:
        stock_code: Stock code (e.g., "005930"). Required when source includes "krx".
        stock_name: Stock name in Korean (e.g., "삼성전자").
        corp_code: DART corporation code (e.g., "00126380").
        source: Data source - "krx", "hyperliquid", or "all".
        coins: Crypto coin symbols for Hyperliquid collection.
        interval: Candle interval for Hyperliquid (e.g. "1h").
        candle_limit: Number of candles to fetch per coin.

    Returns:
        dict with source-tagged collected data and agent result metadata.
    """
    await event_bus.emit(
        EventType.COLLECTION_STARTED,
        {"stock_code": stock_code, "stock_name": stock_name, "source": source},
        source="collection_flow",
    )

    agent = CollectionAgent()
    result = await agent.execute(
        source=source,
        stock_code=stock_code,
        stock_name=stock_name,
        corp_code=corp_code,
        coins=coins,
        interval=interval,
        candle_limit=candle_limit,
    )

    # Build backward-compatible output
    output: dict[str, Any] = {
        "agent_status": result.status,
        "agent_errors": result.errors,
        "agent_metadata": result.metadata,
        "source": source,
    }

    # Merge KRX data at the top level for backward compatibility
    krx_data = result.data.get("krx", {})
    if krx_data:
        output["stock_code"] = krx_data.get("stock_code", stock_code)
        output["stock_name"] = krx_data.get("stock_name", stock_name)
        output["price_data"] = krx_data.get("price_data")
        output["disclosures"] = krx_data.get("disclosures")
        output["news"] = krx_data.get("news")
        output["market_data"] = krx_data.get("market_data")
        output["quality_report"] = krx_data.get("quality_report")

    # Attach Hyperliquid data
    hl_data = result.data.get("hyperliquid")
    if hl_data:
        output["hyperliquid"] = hl_data

    await event_bus.emit(
        EventType.COLLECTION_COMPLETED,
        {
            "stock_code": stock_code,
            "source": source,
            "status": result.status,
            "quality_status": output.get("quality_report", {}).get("overall_status")
            if isinstance(output.get("quality_report"), dict)
            else None,
        },
        source="collection_flow",
    )

    return output
