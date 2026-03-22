"""Analysis flow: Technical → Fundamental → Sentiment (KRX / Hyperliquid).

Orchestrates AnalysisAgent inside Prefect tasks.  The ``source`` parameter
controls which data pipeline is executed:

- "krx"         – Korean equity analysis (technical + fundamental + sentiment)
- "hyperliquid" – Crypto perpetual analysis (technical + volume + volatility)
- "all"         – Both sources in parallel
"""

from typing import Any, Literal

import structlog
from prefect import flow, task

from ai_data_science_team.config.prefect_config import RETRIES, TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus
from src.analysis_service.app.agents.analysis_agent import AnalysisAgent

logger = structlog.get_logger()

SourceType = Literal["krx", "hyperliquid", "all"]

# Shared agent instance (stateless, safe to reuse across task runs)
_analysis_agent = AnalysisAgent()


# ------------------------------------------------------------------
# Prefect tasks – thin wrappers that delegate to AnalysisAgent
# ------------------------------------------------------------------


@task(
    name="run_eda",
    tags=TAGS["analysis"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def run_eda(
    symbol: str,
    collected_data: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Run Exploratory Data Analysis on collected data."""
    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "eda", "status": "started", "symbol": symbol, "source": source},
        source="eda_agent",
    )

    if source in ("krx", "all"):
        result = await _analysis_agent.krx_technical_analysis(symbol, collected_data)
    else:
        result = await _analysis_agent.hyperliquid_technical_analysis(
            symbol, collected_data
        )

    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "eda", "status": "completed", "symbol": symbol},
        source="eda_agent",
    )
    return result


@task(
    name="run_sentiment_analysis",
    tags=TAGS["analysis"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def run_sentiment_analysis(
    symbol: str,
    news_data: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Run sentiment analysis on news articles (KRX only)."""
    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "sentiment", "status": "started", "symbol": symbol},
        source="sentiment_agent",
    )

    if source in ("krx", "all"):
        result = await _analysis_agent.krx_sentiment_analysis(symbol, {"news": news_data})
    else:
        # Hyperliquid has no sentiment pipeline yet; return empty stub
        result = {"overall_sentiment": None, "note": "sentiment not applicable for hyperliquid"}

    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "sentiment", "status": "completed", "symbol": symbol},
        source="sentiment_agent",
    )
    return result


@task(
    name="run_sector_analysis",
    tags=TAGS["analysis"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def run_sector_analysis(
    symbol: str,
    market_data: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Run sector-level analysis and clustering (KRX) or volume analysis (Hyperliquid)."""
    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "sector", "status": "started", "symbol": symbol},
        source="sector_agent",
    )

    if source in ("krx", "all"):
        result = await _analysis_agent.krx_fundamental_analysis(symbol, {"financials": market_data})
    else:
        result = await _analysis_agent.hyperliquid_volume_analysis(symbol, market_data)

    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "sector", "status": "completed", "symbol": symbol},
        source="sector_agent",
    )
    return result


@task(
    name="run_feature_engineering",
    tags=TAGS["analysis"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def run_feature_engineering(
    symbol: str,
    collected_data: dict[str, Any],
    sentiment_result: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Run feature engineering (requires sentiment results for sentiment features)."""
    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "features", "status": "started", "symbol": symbol},
        source="feature_agent",
    )

    # TODO: Integrate dedicated feature engineering logic into AnalysisAgent
    result = {
        "symbol": symbol,
        "source": source,
        "sentiment_input": sentiment_result,
        "status": "pending_implementation",
        "description": "Features: 50+ technical indicators, sentiment features, fundamentals",
    }

    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "features", "status": "completed", "symbol": symbol},
        source="feature_agent",
    )
    return result


@task(
    name="run_statistical_analysis",
    tags=TAGS["analysis"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def run_statistical_analysis(
    symbol: str,
    collected_data: dict[str, Any],
    features: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Run statistical analysis (regression, hypothesis testing, Granger causality)."""
    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "statistical", "status": "started", "symbol": symbol},
        source="statistical_agent",
    )

    if source == "hyperliquid":
        result = await _analysis_agent.hyperliquid_volatility_metrics(
            symbol, collected_data
        )
    else:
        # TODO: Integrate dedicated statistical analysis into AnalysisAgent
        result = {
            "symbol": symbol,
            "source": source,
            "features_input": features,
            "status": "pending_implementation",
            "description": "Stats: regression, Granger causality, cointegration, GARCH",
        }

    await event_bus.emit(
        EventType.ANALYSIS_PROGRESS,
        {"step": "statistical", "status": "completed", "symbol": symbol},
        source="statistical_agent",
    )
    return result


@task(
    name="run_full_analysis",
    tags=TAGS["analysis"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def run_full_analysis(
    symbol: str,
    collected_data: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Run the full AnalysisAgent pipeline (all steps) via agent.execute()."""
    agent_result = await _analysis_agent.execute(
        symbol=symbol,
        collected_data=collected_data,
        source=source,
    )
    return {
        "status": agent_result.status,
        "data": agent_result.data,
        "errors": agent_result.errors,
        "metadata": agent_result.metadata,
    }


# ------------------------------------------------------------------
# Prefect flow
# ------------------------------------------------------------------


@flow(name="analysis_flow", tags=TAGS["analysis"])
async def analysis_flow(
    stock_code: str,
    collected_data: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Main analysis flow with phased execution.

    Phase 1 (parallel): EDA + Sentiment + Sector
    Phase 2 (sequential): Feature Engineering (needs sentiment)
    Phase 3 (sequential): Statistical Analysis (needs features)

    Args:
        stock_code: KRX stock code or Hyperliquid coin symbol.
        collected_data: Raw data from the collection phase.
        source: "krx", "hyperliquid", or "all".

    Returns:
        dict with eda, features, statistical, sentiment, sector results
    """
    await event_bus.emit(
        EventType.ANALYSIS_STARTED,
        {"stock_code": stock_code, "source": source},
        source="analysis_flow",
    )

    # Phase 1: Parallel - EDA, Sentiment, Sector
    eda_future = run_eda.submit(stock_code, collected_data, source)
    sentiment_future = run_sentiment_analysis.submit(
        stock_code, collected_data.get("news", {}), source
    )
    sector_future = run_sector_analysis.submit(
        stock_code, collected_data.get("market_data", {}), source
    )

    eda_result = await eda_future.result()
    sentiment_result = await sentiment_future.result()
    sector_result = await sector_future.result()

    # Phase 2: Sequential - Feature Engineering (needs sentiment)
    feature_result = await run_feature_engineering(
        stock_code, collected_data, sentiment_result, source
    )

    # Phase 3: Sequential - Statistical Analysis (needs features)
    statistical_result = await run_statistical_analysis(
        stock_code, collected_data, feature_result, source
    )

    result = {
        "stock_code": stock_code,
        "source": source,
        "eda": eda_result,
        "features": feature_result,
        "statistical": statistical_result,
        "sentiment": sentiment_result,
        "sector": sector_result,
    }

    await event_bus.emit(
        EventType.ANALYSIS_COMPLETED,
        {"stock_code": stock_code, "source": source},
        source="analysis_flow",
    )

    return result
