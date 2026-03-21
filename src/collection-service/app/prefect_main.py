"""Prefect deployment entrypoint.

Run this to start serving all scheduled and on-demand deployments:
    python -m ai_data_science_team.prefect_main
"""

import asyncio

from ai_data_science_team.flows.deployments import start_all_deployments


def main():
    """Entry point for Prefect deployment server."""
    print("Starting AI Data Science Team - Prefect Deployments")
    print("=" * 50)
    print("Registered deployments:")
    print("  - daily-pipeline      : weekdays 16:00 KST")
    print("  - on-demand-pipeline  : manual trigger")
    print("  - on-demand-collection: manual trigger")
    print("  - intraday-check      : */10 09:00-15:00 KST")
    print("  - disclosure-check    : every 1 hour")
    print("  - news-collection     : every 30 minutes")
    print("  - model-drift-check   : Monday 06:00 KST")
    print("  - mlflow-cleanup      : Sunday 03:00 KST")
    print("=" * 50)
    print("Prefect UI: http://localhost:4200")
    print()

    asyncio.run(start_all_deployments())


if __name__ == "__main__":
    main()
