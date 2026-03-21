"""FastAPI endpoints for KRX Data Collection Microservice."""

from datetime import date, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .async_mdcstat300 import fetch_mdcstat300_async
from .utils import convert_to_standard_code, STOCK_CODE_MAPPING

app = FastAPI(
    title="KRX Data Collection Service",
    description="Microservice for collecting KRX short-selling data",
    version="1.0.0",
)


class CollectRequest(BaseModel):
    """KRX 데이터 수집 요청"""

    stock_code: str = Field(..., description="6자리 또는 12자리 종목코드")
    start_date: str | date = Field(..., description="시작일 (YYYY-MM-DD)")
    end_date: str | date = Field(..., description="종료일 (YYYY-MM-DD)")
    stock_name: str | None = Field(None, description="종목명 (선택)")
    use_proxy: bool = Field(False, description="프록시 사용 여부")
    proxy_url: str | None = Field(None, description="프록시 URL")


class CollectResponse(BaseModel):
    """KRX 데이터 수집 응답"""

    status: str
    stock_code: str
    standard_code: str
    rows: int
    columns: int
    data: list[dict[str, Any]]
    metadata: dict[str, Any]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "krx-collection-service",
        "version": "1.0.0",
    }


@app.get("/api/v1/krx/stocks")
async def list_stocks():
    """지원하는 종목 목록 조회"""
    return {
        "count": len(STOCK_CODE_MAPPING),
        "stocks": [
            {
                "short_code": short,
                "standard_code": standard,
            }
            for short, standard in STOCK_CODE_MAPPING.items()
        ],
    }


@app.post("/api/v1/krx/collect", response_model=CollectResponse)
async def collect_krx_data(request: CollectRequest):
    """
    KRX 공매도 데이터 수집

    Args:
        request: CollectRequest

    Returns:
        CollectResponse with data

    Raises:
        HTTPException: 400 (잘못된 요청), 500 (수집 실패)
    """
    # 6자리 코드를 12자리로 변환
    stock_code = request.stock_code
    if len(stock_code) == 6:
        standard_code = convert_to_standard_code(stock_code)
        if not standard_code:
            raise HTTPException(
                status_code=400,
                detail=f"종목코드 '{stock_code}'는 지원하지 않습니다. "
                f"지원 종목: /api/v1/krx/stocks",
            )
    elif len(stock_code) == 12:
        standard_code = stock_code
        # Reverse lookup for short code
        stock_code = next(
            (k for k, v in STOCK_CODE_MAPPING.items() if v == standard_code),
            stock_code[:6] if stock_code.startswith("KR") else stock_code,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="종목코드는 6자리 또는 12자리여야 합니다.",
        )

    # 종목명 생성 (없으면 코드 사용)
    stock_name = request.stock_name or stock_code

    try:
        df, raw = await fetch_mdcstat300_async(
            isu_cd=standard_code,
            start_date=request.start_date,
            end_date=request.end_date,
            bld="dbms/MDC_OUT/STAT/srt/MDCSTAT30001_OUT",
            extra_payload={
                "locale": "ko_KR",
                "tboxisuCd_finder_srtisu0": f"{stock_code}/{stock_name}",
            },
            proxy=request.proxy_url if request.use_proxy else None,
        )

        # DataFrame을 dict 리스트로 변환
        data = df.to_dict(orient="records")

        return CollectResponse(
            status="success",
            stock_code=stock_code,
            standard_code=standard_code,
            rows=len(df),
            columns=len(df.columns),
            data=data,
            metadata={
                "start_date": str(request.start_date),
                "end_date": str(request.end_date),
                "stock_name": stock_name,
                "columns": df.columns.tolist(),
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"KRX 데이터 수집 실패: {str(e)}",
        )


@app.get("/api/v1/krx/collect/{stock_code}")
async def collect_krx_data_get(
    stock_code: str,
    days: int = 30,
    use_proxy: bool = False,
):
    """
    GET 방식 KRX 데이터 수집 (간편 API)

    Args:
        stock_code: 6자리 또는 12자리 종목코드
        days: 수집 기간 (일)
        use_proxy: 프록시 사용 여부

    Returns:
        CollectResponse
    """
    end_date = datetime.now().date()
    start_date = end_date - datetime.timedelta(days=days)

    return await collect_krx_data(
        CollectRequest(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            use_proxy=use_proxy,
        )
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
