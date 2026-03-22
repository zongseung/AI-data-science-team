"""Prefect deployments: registers all scheduled flows using serve().

Uses serve() for single-process deployment where DataFrame/model objects
can be passed by reference without serialization overhead.
"""

from prefect import serve

from ai_data_science_team.flows.master_flow import master_flow
from ai_data_science_team.flows.collection_flow import collection_flow
from ai_data_science_team.flows.scheduled.daily_pipeline import daily_pipeline
from ai_data_science_team.flows.scheduled.intraday_check import intraday_check
from ai_data_science_team.flows.scheduled.disclosure_check import disclosure_check
from ai_data_science_team.flows.scheduled.news_collection import news_collection
from ai_data_science_team.flows.scheduled.model_drift_check import model_drift_check
from ai_data_science_team.flows.scheduled.mlflow_cleanup import mlflow_cleanup
from ai_data_science_team.config.prefect_config import SCHEDULES


def create_deployments():
    """Create all Prefect deployments with their schedules."""

    # Daily full pipeline at 16:00 KST weekdays
    daily_pipeline_deployment = daily_pipeline.to_deployment(
        name="daily-pipeline",
        cron=SCHEDULES["daily_pipeline"]["cron"],
        timezone=SCHEDULES["daily_pipeline"]["timezone"],
        tags=["scheduled", "daily"],
    )

    # On-demand: triggered by Telegram or API
    on_demand_master_deployment = master_flow.to_deployment(
        name="on-demand-pipeline",
        tags=["on-demand"],
    )

    # On-demand: collection only
    on_demand_collection_deployment = collection_flow.to_deployment(
        name="on-demand-collection",
        tags=["on-demand", "collection"],
    )

    # Intraday price check every 10 min during market hours
    intraday_deployment = intraday_check.to_deployment(
        name="intraday-check",
        cron=SCHEDULES["intraday_check"]["cron"],
        timezone=SCHEDULES["intraday_check"]["timezone"],
        tags=["scheduled", "intraday"],
    )

    # Disclosure check every hour
    disclosure_deployment = disclosure_check.to_deployment(
        name="disclosure-check",
        interval=SCHEDULES["disclosure_check"]["interval"],
        tags=["scheduled", "disclosure"],
    )

    # News collection every 30 minutes
    news_deployment = news_collection.to_deployment(
        name="news-collection",
        interval=SCHEDULES["news_collection"]["interval"],
        tags=["scheduled", "news"],
    )

    # Weekly Monday model drift check
    model_drift_deployment = model_drift_check.to_deployment(
        name="model-drift-check",
        cron=SCHEDULES["model_drift_check"]["cron"],
        timezone=SCHEDULES["model_drift_check"]["timezone"],
        tags=["scheduled", "weekly"],
    )

    # Weekly Sunday MLflow cleanup
    mlflow_cleanup_deployment = mlflow_cleanup.to_deployment(
        name="mlflow-cleanup",
        cron=SCHEDULES["mlflow_cleanup"]["cron"],
        timezone=SCHEDULES["mlflow_cleanup"]["timezone"],
        tags=["scheduled", "weekly", "maintenance"],
    )

    return (
        daily_pipeline_deployment,
        on_demand_master_deployment,
        on_demand_collection_deployment,
        intraday_deployment,
        disclosure_deployment,
        news_deployment,
        model_drift_deployment,
        mlflow_cleanup_deployment,
    )


async def start_all_deployments():
    """Start serving all deployments in a single process."""
    deployments = create_deployments()
    await serve(*deployments)
