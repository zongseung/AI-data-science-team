"""Telegram → Prefect flow trigger integration.

Maps Telegram commands to Prefect flow invocations.
"""

from typing import Any

from ai_data_science_team.config.constants import STOCK_CODES
from ai_data_science_team.flows.collection_flow import collection_flow
from ai_data_science_team.flows.master_flow import master_flow


def resolve_stock_name(query: str) -> dict[str, str] | None:
    """Resolve a user query to stock info.

    Supports exact match and partial match on stock names.
    """
    # Exact match
    if query in STOCK_CODES:
        return {"stock_name": query, **STOCK_CODES[query]}

    # Partial match
    for name, info in STOCK_CODES.items():
        if query in name:
            return {"stock_name": name, **info}

    return None


async def trigger_full_pipeline(stock_query: str) -> dict[str, Any]:
    """Trigger full E2E pipeline from Telegram command.

    Usage: /리포트 삼성전자
    """
    stock = resolve_stock_name(stock_query)
    if not stock:
        return {
            "status": "error",
            "message": f"종목 '{stock_query}'을 찾을 수 없습니다.",
        }

    result = await master_flow(
        stock_code=stock["stock_code"],
        stock_name=stock["stock_name"],
        corp_code=stock["corp_code"],
    )

    return {
        "status": "completed",
        "message": result.get("report", {}).get("telegram_message", "완료"),
        "stock_name": stock["stock_name"],
    }


async def trigger_collection(stock_query: str) -> dict[str, Any]:
    """Trigger data collection from Telegram command.

    Usage: /수집 삼성전자
    """
    stock = resolve_stock_name(stock_query)
    if not stock:
        return {
            "status": "error",
            "message": f"종목 '{stock_query}'을 찾을 수 없습니다.",
        }

    result = await collection_flow(
        stock_code=stock["stock_code"],
        stock_name=stock["stock_name"],
        corp_code=stock["corp_code"],
    )

    quality = result.get("quality_report", {})
    return {
        "status": "completed",
        "message": (
            f"{stock['stock_name']} 데이터 수집 완료\n"
            f"품질: {quality.get('overall_status', 'unknown')}\n"
            f"검사항목: {len(quality.get('checks', []))}건\n"
            f"경고: {len(quality.get('warnings', []))}건"
        ),
        "stock_name": stock["stock_name"],
    }
