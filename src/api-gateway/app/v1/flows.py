"""Prefect flow trigger API endpoints.

Provides HTTP endpoints for on-demand flow triggering from
the web UI or external services.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai_data_science_team.config.constants import STOCK_CODES
from ai_data_science_team.flows.collection_flow import collection_flow
from ai_data_science_team.flows.master_flow import master_flow

router = APIRouter()


class FlowTriggerRequest(BaseModel):
    """Request body for triggering a flow."""

    stock_name: str


class FlowTriggerResponse(BaseModel):
    """Response after triggering a flow."""

    status: str
    message: str
    stock_code: str | None = None


def _resolve_stock(stock_name: str) -> dict[str, str]:
    """Resolve stock name to stock_code and corp_code."""
    stock_info = STOCK_CODES.get(stock_name)
    if not stock_info:
        raise HTTPException(
            status_code=404,
            detail=f"종목 '{stock_name}'을 찾을 수 없습니다. 등록된 종목: {list(STOCK_CODES.keys())}",
        )
    return {"stock_name": stock_name, **stock_info}


@router.post("/trigger/full-pipeline", response_model=FlowTriggerResponse)
async def trigger_full_pipeline(request: FlowTriggerRequest):
    """Trigger the full E2E pipeline for a stock.

    This runs: Collection → Analysis → Forecast → Report
    """
    stock = _resolve_stock(request.stock_name)

    # Run as a Prefect flow (non-blocking via submit would require work pool)
    # For now, run synchronously in the request
    await master_flow(
        stock_code=stock["stock_code"],
        stock_name=stock["stock_name"],
        corp_code=stock["corp_code"],
    )

    return FlowTriggerResponse(
        status="completed",
        message=f"{stock['stock_name']} 전체 파이프라인 완료",
        stock_code=stock["stock_code"],
    )


@router.post("/trigger/collection", response_model=FlowTriggerResponse)
async def trigger_collection(request: FlowTriggerRequest):
    """Trigger data collection only for a stock."""
    stock = _resolve_stock(request.stock_name)

    await collection_flow(
        stock_code=stock["stock_code"],
        stock_name=stock["stock_name"],
        corp_code=stock["corp_code"],
    )

    return FlowTriggerResponse(
        status="completed",
        message=f"{stock['stock_name']} 데이터 수집 완료",
        stock_code=stock["stock_code"],
    )


@router.get("/stocks")
async def list_stocks():
    """List all registered stocks and their codes."""
    return {
        name: info
        for name, info in STOCK_CODES.items()
    }
