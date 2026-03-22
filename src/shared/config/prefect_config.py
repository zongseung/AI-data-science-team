"""Prefect configuration: schedules, tags, timeouts."""

from datetime import timedelta

# Cron schedules (Asia/Seoul timezone)
TIMEZONE = "Asia/Seoul"

SCHEDULES = {
    "daily_pipeline": {"cron": "0 16 * * 1-5", "timezone": TIMEZONE},
    "forecast_evaluation": {"cron": "10 16 * * 1-5", "timezone": TIMEZONE},
    "intraday_check": {"cron": "*/10 9-15 * * 1-5", "timezone": TIMEZONE},
    "disclosure_check": {"interval": timedelta(hours=1)},
    "news_collection": {"interval": timedelta(minutes=30)},
    "model_drift_check": {"cron": "0 6 * * 1", "timezone": TIMEZONE},
    "mlflow_cleanup": {"cron": "0 3 * * 0", "timezone": TIMEZONE},
}

# Flow tags
TAGS = {
    "collection": ["collection", "data-pipeline"],
    "analysis": ["analysis", "data-science"],
    "forecast": ["forecast", "ml-engineering"],
    "report": ["report", "generation"],
    "scheduled": ["scheduled", "automated"],
    "on_demand": ["on-demand", "manual"],
}

# Timeouts
TIMEOUTS = {
    "collection_flow": timedelta(minutes=10),
    "analysis_flow": timedelta(minutes=30),
    "forecast_flow": timedelta(minutes=60),
    "report_flow": timedelta(minutes=15),
    "master_flow": timedelta(hours=2),
    "single_collector": timedelta(minutes=5),
    "single_agent": timedelta(minutes=10),
}

# Retry configuration
RETRIES = {
    "collector": {"retries": 3, "retry_delay_seconds": 10},
    "agent": {"retries": 2, "retry_delay_seconds": 30},
    "flow": {"retries": 1, "retry_delay_seconds": 60},
}
