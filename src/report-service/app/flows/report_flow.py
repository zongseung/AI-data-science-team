"""Report flow: Comprehensive Report + Investment Memo + Risk Note → Editor Review.

Orchestrates report generation agents:
- Parallel: Comprehensive report + Investment memo + Risk note
- Sequential: Editor review (final quality check)
"""

from typing import Any

from prefect import flow, task

from ai_data_science_team.config.prefect_config import RETRIES, TAGS
from ai_data_science_team.services.event_bus import EventType, event_bus


@task(
    name="write_comprehensive_report",
    tags=TAGS["report"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def write_comprehensive_report(
    stock_code: str,
    collection_data: dict[str, Any],
    analysis_data: dict[str, Any],
    ml_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate comprehensive analysis report synthesizing all data."""
    await event_bus.emit(
        EventType.REPORT_PROGRESS,
        {"step": "comprehensive", "status": "started", "stock_code": stock_code},
        source="comprehensive_reporter",
    )
    # TODO: Integrate Comprehensive Reporter agent from agents/report/
    result = {
        "stock_code": stock_code,
        "status": "pending_implementation",
        "report_type": "comprehensive",
        "description": "Full analysis report with all team results",
    }
    await event_bus.emit(
        EventType.REPORT_PROGRESS,
        {"step": "comprehensive", "status": "completed", "stock_code": stock_code},
        source="comprehensive_reporter",
    )
    return result


@task(
    name="write_investment_memo",
    tags=TAGS["report"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def write_investment_memo(
    stock_code: str,
    ml_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate investment memo with ML predictions and backtest results."""
    await event_bus.emit(
        EventType.REPORT_PROGRESS,
        {"step": "investment_memo", "status": "started", "stock_code": stock_code},
        source="investment_memo_writer",
    )
    # TODO: Integrate Investment Memo agent from agents/report/
    result = {
        "stock_code": stock_code,
        "status": "pending_implementation",
        "report_type": "investment_memo",
        "description": "Investment thesis from ML predictions + backtest",
    }
    await event_bus.emit(
        EventType.REPORT_PROGRESS,
        {"step": "investment_memo", "status": "completed", "stock_code": stock_code},
        source="investment_memo_writer",
    )
    return result


@task(
    name="write_risk_note",
    tags=TAGS["report"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def write_risk_note(
    stock_code: str,
    ml_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate risk warning note with VaR/CVaR analysis."""
    await event_bus.emit(
        EventType.REPORT_PROGRESS,
        {"step": "risk_note", "status": "started", "stock_code": stock_code},
        source="risk_note_writer",
    )
    # TODO: Integrate Risk Note agent from agents/report/
    result = {
        "stock_code": stock_code,
        "status": "pending_implementation",
        "report_type": "risk_note",
        "description": "Risk warnings by severity from VaR/CVaR",
    }
    await event_bus.emit(
        EventType.REPORT_PROGRESS,
        {"step": "risk_note", "status": "completed", "stock_code": stock_code},
        source="risk_note_writer",
    )
    return result


@task(
    name="editor_review",
    tags=TAGS["report"],
    retries=RETRIES["agent"]["retries"],
    retry_delay_seconds=RETRIES["agent"]["retry_delay_seconds"],
)
async def editor_review(
    stock_code: str,
    comprehensive: dict[str, Any],
    investment_memo: dict[str, Any],
    risk_note: dict[str, Any],
) -> dict[str, Any]:
    """Editor-in-chief reviews and finalizes all reports."""
    await event_bus.emit(
        EventType.REPORT_PROGRESS,
        {"step": "editor_review", "status": "started", "stock_code": stock_code},
        source="report_editor",
    )
    # TODO: Integrate Report Editor agent from agents/report/
    result = {
        "stock_code": stock_code,
        "status": "pending_implementation",
        "description": "Final review, quality validation, Telegram formatting",
        "comprehensive": comprehensive,
        "investment_memo": investment_memo,
        "risk_note": risk_note,
        "telegram_message": f"[{stock_code}] 분석 보고서가 준비되었습니다.",
    }
    await event_bus.emit(
        EventType.REPORT_PROGRESS,
        {"step": "editor_review", "status": "completed", "stock_code": stock_code},
        source="report_editor",
    )
    return result


@flow(name="report_flow", tags=TAGS["report"])
async def report_flow(
    stock_code: str,
    collection_data: dict[str, Any],
    analysis_data: dict[str, Any],
    ml_data: dict[str, Any],
) -> dict[str, Any]:
    """Main report flow.

    Parallel: Comprehensive report + Investment memo + Risk note
    Sequential: Editor review

    Returns:
        dict with comprehensive, investment_memo, risk_note, final, telegram_message
    """
    await event_bus.emit(
        EventType.REPORT_STARTED,
        {"stock_code": stock_code},
        source="report_flow",
    )

    # Parallel: Generate 3 reports
    comprehensive_future = write_comprehensive_report.submit(
        stock_code, collection_data, analysis_data, ml_data
    )
    memo_future = write_investment_memo.submit(stock_code, ml_data)
    risk_future = write_risk_note.submit(stock_code, ml_data)

    comprehensive = await comprehensive_future.result()
    investment_memo = await memo_future.result()
    risk_note = await risk_future.result()

    # Sequential: Editor review
    final = await editor_review(
        stock_code, comprehensive, investment_memo, risk_note
    )

    result = {
        "stock_code": stock_code,
        "comprehensive": comprehensive,
        "investment_memo": investment_memo,
        "risk_note": risk_note,
        "final": final,
        "telegram_message": final.get("telegram_message", ""),
    }

    await event_bus.emit(
        EventType.REPORT_COMPLETED,
        {"stock_code": stock_code},
        source="report_flow",
    )

    return result
