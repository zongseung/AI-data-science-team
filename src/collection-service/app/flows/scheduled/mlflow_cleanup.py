"""MLflow cleanup: weekly Sunday cleanup of old experiments and artifacts."""

from prefect import flow

from ai_data_science_team.config.prefect_config import TAGS


@flow(name="mlflow_cleanup", tags=TAGS["scheduled"])
async def mlflow_cleanup(keep_days: int = 30):
    """Clean up old MLflow experiments and artifacts.

    Runs weekly on Sunday at 03:00 KST.
    Keeps experiments from the last `keep_days` days.
    """
    # TODO: Implement once MLflow service is integrated
    # 1. List experiments older than keep_days
    # 2. Delete old runs and artifacts
    # 3. Log cleanup summary

    return {
        "status": "pending_implementation",
        "keep_days": keep_days,
        "description": "MLflow experiment and artifact cleanup",
    }
