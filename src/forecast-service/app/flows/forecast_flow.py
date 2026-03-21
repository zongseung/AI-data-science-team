"""Forecast flow: Model Training → Backtest + Risk Assessment.

Orchestrates ML model training sequentially, then runs backtesting and
risk assessment in parallel.
"""

from typing import Any

from prefect import flow, task

from ai_data_science_team.config.prefect_config import RETRIES, TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus


@task(
    name="train_models",
    tags=TAGS["forecast"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def train_models(
    stock_code: str, analysis_data: dict[str, Any]
) -> dict[str, Any]:
    """Train ML models: Prophet, LSTM, XGBoost, LightGBM + ensemble."""
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "training", "status": "started", "stock_code": stock_code},
        source="model_training_agent",
    )
    # TODO: Integrate Model Training agent from agents/forecast/
    result = {
        "stock_code": stock_code,
        "status": "pending_implementation",
        "models": ["Prophet", "LSTM", "XGBoost", "LightGBM"],
        "description": "Model training with Optuna HPO + ensemble",
    }
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "training", "status": "completed", "stock_code": stock_code},
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
    stock_code: str, ml_results: dict[str, Any]
) -> dict[str, Any]:
    """Run backtesting: walk-forward validation, strategy simulation."""
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "backtest", "status": "started", "stock_code": stock_code},
        source="backtest_agent",
    )
    # TODO: Integrate Backtest agent from agents/forecast/
    result = {
        "stock_code": stock_code,
        "status": "pending_implementation",
        "description": "Backtest: walk-forward, Sharpe, Sortino, MDD, Calmar",
    }
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "backtest", "status": "completed", "stock_code": stock_code},
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
    stock_code: str, ml_results: dict[str, Any]
) -> dict[str, Any]:
    """Assess risk: VaR, CVaR, Monte Carlo simulation, GARCH volatility."""
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "risk", "status": "started", "stock_code": stock_code},
        source="risk_agent",
    )
    # TODO: Integrate Risk Assessment agent from agents/forecast/
    result = {
        "stock_code": stock_code,
        "status": "pending_implementation",
        "description": "Risk: VaR, CVaR, Monte Carlo, GARCH",
    }
    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "risk", "status": "completed", "stock_code": stock_code},
        source="risk_agent",
    )
    return result


@flow(name="forecast_flow", tags=TAGS["forecast"])
async def forecast_flow(
    stock_code: str,
    analysis_data: dict[str, Any],
) -> dict[str, Any]:
    """Main forecast flow.

    Sequential: Model training
    Parallel: Backtesting + Risk assessment

    Returns:
        dict with ml_results, backtest, risk
    """
    await event_bus.emit(
        EventType.FORECAST_STARTED,
        {"stock_code": stock_code},
        source="forecast_flow",
    )

    # Sequential: Train models first
    ml_results = await train_models(stock_code, analysis_data)

    # Parallel: Backtest + Risk assessment
    backtest_future = run_backtest.submit(stock_code, ml_results)
    risk_future = assess_risk.submit(stock_code, ml_results)

    backtest_result = await backtest_future.result()
    risk_result = await risk_future.result()

    result = {
        "stock_code": stock_code,
        "ml_results": ml_results,
        "backtest": backtest_result,
        "risk": risk_result,
    }

    await event_bus.emit(
        EventType.FORECAST_COMPLETED,
        {"stock_code": stock_code},
        source="forecast_flow",
    )

    return result
