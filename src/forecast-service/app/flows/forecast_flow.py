"""Forecast flow: Model Training → Backtest + Risk Assessment.

Orchestrates ForecastAgent inside Prefect tasks.  The ``source`` parameter
controls which pipeline runs:

- "krx"         – Stock price prediction, backtesting, risk (VaR/Monte Carlo)
- "hyperliquid" – Crypto prediction, volatility forecast, liquidation risk
- "all"         – Both sources in parallel
"""

from typing import Any, Literal

import structlog
from prefect import flow, task

from ai_data_science_team.config.prefect_config import RETRIES, TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus
from src.forecast_service.app.agents.forecast_agent import ForecastAgent

logger = structlog.get_logger()

SourceType = Literal["krx", "hyperliquid", "all"]

# Shared agent instance (stateless, safe to reuse across task runs)
_forecast_agent = ForecastAgent()


# ------------------------------------------------------------------
# Prefect tasks – thin wrappers that delegate to ForecastAgent
# ------------------------------------------------------------------


@task(
    name="train_models",
    tags=TAGS["forecast"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def train_models(
    symbol: str,
    analysis_data: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Train ML models: Prophet, LSTM (KRX) or crypto prediction (Hyperliquid)."""
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "training", "status": "started", "symbol": symbol, "source": source},
        source="model_training_agent",
    )

    if source == "hyperliquid":
        result = await _forecast_agent.hyperliquid_price_prediction(
            symbol, analysis_data
        )
    else:
        result = await _forecast_agent.krx_price_prediction(symbol, analysis_data)

    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "training", "status": "completed", "symbol": symbol},
        source="model_training_agent",
    )
    return result


@task(
    name="run_backtest",
    tags=TAGS["forecast"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def run_backtest(
    symbol: str,
    ml_results: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Run backtesting (KRX) or volatility forecast (Hyperliquid)."""
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "backtest", "status": "started", "symbol": symbol},
        source="backtest_agent",
    )

    if source == "hyperliquid":
        result = await _forecast_agent.hyperliquid_volatility_forecast(
            symbol, ml_results
        )
    else:
        result = await _forecast_agent.krx_backtesting(symbol, ml_results)

    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "backtest", "status": "completed", "symbol": symbol},
        source="backtest_agent",
    )
    return result


@task(
    name="assess_risk",
    tags=TAGS["forecast"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def assess_risk(
    symbol: str,
    ml_results: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Assess risk: VaR/Monte Carlo (KRX) or liquidation risk (Hyperliquid)."""
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "risk", "status": "started", "symbol": symbol},
        source="risk_agent",
    )

    if source == "hyperliquid":
        result = await _forecast_agent.hyperliquid_liquidation_risk(
            symbol, ml_results
        )
    else:
        result = await _forecast_agent.krx_risk_assessment(symbol, ml_results)

    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "risk", "status": "completed", "symbol": symbol},
        source="risk_agent",
    )
    return result


@task(
    name="run_full_forecast",
    tags=TAGS["forecast"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def run_full_forecast(
    symbol: str,
    analysis_data: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Run the full ForecastAgent pipeline (all steps) via agent.execute()."""
    agent_result = await _forecast_agent.execute(
        symbol=symbol,
        analysis_data=analysis_data,
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


@flow(name="forecast_flow", tags=TAGS["forecast"])
async def forecast_flow(
    stock_code: str,
    analysis_data: dict[str, Any],
    source: SourceType = "krx",
) -> dict[str, Any]:
    """Main forecast flow.

    Sequential: Model training / price prediction
    Parallel: Backtesting + Risk assessment

    Args:
        stock_code: KRX stock code or Hyperliquid coin symbol.
        analysis_data: Results from the analysis phase.
        source: "krx", "hyperliquid", or "all".

    Returns:
        dict with ml_results, backtest, risk
    """
    await event_bus.emit(
        EventType.FORECAST_STARTED,
        {"stock_code": stock_code, "source": source},
        source="forecast_flow",
    )

    # Sequential: Train models / generate predictions first
    ml_results = await train_models(stock_code, analysis_data, source)

    # Parallel: Backtest + Risk assessment
    backtest_future = run_backtest.submit(stock_code, ml_results, source)
    risk_future = assess_risk.submit(stock_code, ml_results, source)

    backtest_result = await backtest_future.result()
    risk_result = await risk_future.result()

    result = {
        "stock_code": stock_code,
        "source": source,
        "ml_results": ml_results,
        "backtest": backtest_result,
        "risk": risk_result,
    }

    await event_bus.emit(
        EventType.FORECAST_COMPLETED,
        {"stock_code": stock_code, "source": source},
        source="forecast_flow",
    )

    return result
