"""Master flow: E2E pipeline from collection → analysis → forecast → report.

This is the main entry point for the full pipeline, typically triggered:
- Daily at 16:00 KST (scheduled)
- On-demand via Telegram or API
"""

from typing import Any

from prefect import flow

from ai_data_science_team.config.prefect_config import TAGS
from ai_data_science_team.flows.collection_flow import collection_flow
from ai_data_science_team.flows.analysis_flow import analysis_flow
from ai_data_science_team.flows.forecast_flow import forecast_flow
from ai_data_science_team.flows.report_flow import report_flow
from ai_data_science_team.services.event_bus import EventType, event_bus


@flow(
    name="master_flow",
    tags=TAGS["scheduled"] + TAGS["on_demand"],
)
async def master_flow(
    stock_code: str,
    stock_name: str,
    corp_code: str,
) -> dict[str, Any]:
    """End-to-end pipeline: Collection → Analysis → Forecast → Report.

    Args:
        stock_code: Stock code (e.g., "005930")
        stock_name: Stock name in Korean (e.g., "삼성전자")
        corp_code: DART corporation code (e.g., "00126380")

    Returns:
        dict with all pipeline results including final reports
    """
    await event_bus.emit(
        EventType.PIPELINE_STARTED,
        {"stock_code": stock_code, "stock_name": stock_name},
        source="master_flow",
    )

    try:
        # Step 1: Data Collection
        collected_data = await collection_flow(
            stock_code=stock_code,
            stock_name=stock_name,
            corp_code=corp_code,
        )

        # Step 2: Analysis
        analysis_data = await analysis_flow(
            stock_code=stock_code,
            collected_data=collected_data,
        )

        # Step 3: Forecast
        forecast_data = await forecast_flow(
            stock_code=stock_code,
            analysis_data=analysis_data,
        )

        # Step 4: Report
        report_data = await report_flow(
            stock_code=stock_code,
            collection_data=collected_data,
            analysis_data=analysis_data,
            ml_data=forecast_data,
        )

        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "collection": collected_data,
            "analysis": analysis_data,
            "forecast": forecast_data,
            "report": report_data,
        }

        await event_bus.emit(
            EventType.PIPELINE_COMPLETED,
            {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "telegram_message": report_data.get("telegram_message", ""),
            },
            source="master_flow",
        )

        return result

    except Exception as e:
        await event_bus.emit(
            EventType.PIPELINE_FAILED,
            {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "error": str(e),
            },
            source="master_flow",
        )
        raise
