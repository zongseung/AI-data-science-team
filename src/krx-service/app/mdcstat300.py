from __future__ import annotations

from datetime import date, datetime
from typing import Any

import polars as pl

from ._helpers import normalize_yyyymmdd, pick_table, parse_krx_df
from .client import KRXClient


def fetch_mdcstat300(
    *,
    isu_cd: str,
    start_date: str | date | datetime,
    end_date: str | date | datetime,
    bld: str,
    screen_id: str = "MDCSTAT300",
    extra_payload: dict[str, Any] | None = None,
) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Fetch KRX MDCSTAT300 data and return (DataFrame, raw_json)."""
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

    with KRXClient() as client:
        client.warmup(screen_id=screen_id, isu_cd=isu_cd)
        raw = client.post_json(bld=bld, payload=payload)

    return parse_krx_df(pick_table(raw)), raw
