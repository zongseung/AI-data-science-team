"""Model drift check: weekly Monday check for prediction accuracy degradation."""

from prefect import flow

from ai_data_science_team.config.prefect_config import TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus


@flow(name="model_drift_check", tags=TAGS["scheduled"] + TAGS["forecast"])
async def model_drift_check():
    """Check for model drift by comparing recent predictions vs actuals.

    Runs weekly on Monday at 06:00 KST.
    """
    # TODO: Implement once forecast agents are built
    # 1. Fetch recent predictions from Supabase
    # 2. Compare with actual prices
    # 3. Calculate drift metrics (MAE, RMSE change over time)
    # 4. Alert if drift exceeds threshold

    await event_bus.emit(
        EventType.FORECAST_PROGRESS,
        {"step": "drift_check", "status": "pending_implementation"},
        source="model_drift_check",
    )

    return {
        "status": "pending_implementation",
        "description": "Model drift detection with MAE/RMSE monitoring",
    }
