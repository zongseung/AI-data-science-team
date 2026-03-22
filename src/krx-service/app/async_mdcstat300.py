"""Async version of MDCSTAT300 data fetcher."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import polars as pl

from ._helpers import normalize_yyyymmdd, pick_table, parse_krx_df
from .async_client import AsyncKRXClient


async def fetch_mdcstat300_async(
    *,
    isu_cd: str,
    start_date: str | date | datetime,
    end_date: str | date | datetime,
    bld: str,
    screen_id: str = "MDCSTAT300",
    extra_payload: dict[str, Any] | None = None,
    proxy: str | None = None,
    proxy_auth: tuple[str, str] | None = None,
) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Async fetch KRX MDCSTAT300 data with optional proxy.

    Args:
        isu_cd: 12-digit standard code (e.g., "KR7033640004")
        start_date: Start date
        end_date: End date
        bld: KRX bld parameter (e.g., "dbms/MDC_OUT/STAT/srt/MDCSTAT30001_OUT")
        screen_id: Screen ID (default: "MDCSTAT300")
        extra_payload: Additional payload parameters
        proxy: Proxy URL (e.g., "http://proxy.example.com:8080")
        proxy_auth: Proxy authentication (username, password)

    Returns:
        (DataFrame, raw_json)
    """
    payload: dict[str, Any] = {
        "isuCd": isu_cd,
        "strtDd": normalize_yyyymmdd(start_date),
        "endDd": normalize_yyyymmdd(end_date),
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false",
    }
    if extra_payload:
        payload.update(extra_payload)

    async with AsyncKRXClient(proxy=proxy, proxy_auth=proxy_auth) as client:
        await client.warmup(screen_id=screen_id, isu_cd=isu_cd)
        raw = await client.post_json(bld=bld, payload=payload)

    return parse_krx_df(pick_table(raw)), raw
