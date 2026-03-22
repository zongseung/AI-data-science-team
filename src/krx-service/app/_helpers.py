"""Shared helpers for KRX data fetching and parsing."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import polars as pl


def normalize_yyyymmdd(value: str | date | datetime) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d")
    if isinstance(value, date):
        return value.strftime("%Y%m%d")

    s = value.strip()
    if len(s) == 8 and s.isdigit():
        return s
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise ValueError("Date must be YYYYMMDD or YYYY-MM-DD") from exc


def pick_table(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("OutBlock_1", "output", "block1", "result"):
        value = data.get(key)
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            return value

    for value in data.values():
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            return value

    raise ValueError(f"No table-like list found in response keys={list(data.keys())}")


def parse_krx_df(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """KRX raw rows → 타입이 지정된 Polars DataFrame.

    - TRD_DD: Date
    - 나머지: 콤마 제거 + '-' → null 후 Int64
    """
    df = pl.DataFrame(rows)

    exprs: list[pl.Expr] = []
    for col in df.columns:
        if col == "TRD_DD":
            exprs.append(pl.col(col).str.to_date("%Y/%m/%d"))
        else:
            exprs.append(
                pl.col(col)
                .str.replace_all(",", "")
                .replace("-", None)
                .cast(pl.Int64)
            )

    return df.with_columns(exprs)
