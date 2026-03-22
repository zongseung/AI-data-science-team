"""Technical indicator calculations from OHLCV candle data.

Pure numpy — no external TA library needed.
Input: list of candle dicts with keys: open, high, low, close, volume
"""

from __future__ import annotations

import numpy as np
from typing import Any


def _to_arrays(candles: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    """Convert candle list to numpy arrays."""
    return {
        "open": np.array([float(c.get("open", c.get("o", 0))) for c in candles]),
        "high": np.array([float(c.get("high", c.get("h", 0))) for c in candles]),
        "low": np.array([float(c.get("low", c.get("l", 0))) for c in candles]),
        "close": np.array([float(c.get("close", c.get("c", 0))) for c in candles]),
        "volume": np.array([float(c.get("volume", c.get("v", 0))) for c in candles]),
    }


# ── SMA ──────────────────────────────────────────────────────────────────

def sma(closes: np.ndarray, period: int) -> float | None:
    """Simple Moving Average (latest value)."""
    if len(closes) < period:
        return None
    return float(np.mean(closes[-period:]))


def sma_series(closes: np.ndarray, period: int) -> np.ndarray:
    """Full SMA series (NaN-padded)."""
    if len(closes) < period:
        return np.full(len(closes), np.nan)
    kernel = np.ones(period) / period
    result = np.convolve(closes, kernel, mode='valid')
    return np.concatenate([np.full(period - 1, np.nan), result])


# ── EMA ──────────────────────────────────────────────────────────────────

def ema(closes: np.ndarray, period: int) -> float | None:
    """Exponential Moving Average (latest value)."""
    if len(closes) < period:
        return None
    multiplier = 2 / (period + 1)
    ema_val = float(np.mean(closes[:period]))  # SMA seed
    for price in closes[period:]:
        ema_val = (float(price) - ema_val) * multiplier + ema_val
    return ema_val


def ema_series(closes: np.ndarray, period: int) -> np.ndarray:
    """Full EMA series."""
    if len(closes) < period:
        return np.full(len(closes), np.nan)
    result = np.full(len(closes), np.nan)
    multiplier = 2 / (period + 1)
    result[period - 1] = float(np.mean(closes[:period]))
    for i in range(period, len(closes)):
        result[i] = (float(closes[i]) - result[i - 1]) * multiplier + result[i - 1]
    return result


# ── RSI ──────────────────────────────────────────────────────────────────

def rsi(closes: np.ndarray, period: int = 14) -> float | None:
    """Relative Strength Index (Wilder's smoothing)."""
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + float(gains[i])) / period
        avg_loss = (avg_loss * (period - 1) + float(losses[i])) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


# ── MACD ─────────────────────────────────────────────────────────────────

def macd(
    closes: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> dict[str, float | None]:
    """MACD line, signal line, histogram."""
    if len(closes) < slow + signal_period:
        return {"macd_line": None, "signal_line": None, "histogram": None}

    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    macd_line = ema_fast - ema_slow

    # Signal = EMA of MACD line (only valid portion)
    valid_macd = macd_line[~np.isnan(macd_line)]
    if len(valid_macd) < signal_period:
        return {"macd_line": None, "signal_line": None, "histogram": None}

    signal_val = ema(valid_macd, signal_period)
    macd_val = float(valid_macd[-1])
    hist = macd_val - (signal_val or 0)

    return {
        "macd_line": round(macd_val, 6),
        "signal_line": round(signal_val, 6) if signal_val else None,
        "histogram": round(hist, 6),
    }


# ── Bollinger Bands ──────────────────────────────────────────────────────

def bollinger_bands(
    closes: np.ndarray, period: int = 20, num_std: float = 2.0,
) -> dict[str, float | None]:
    """Bollinger Bands (upper, middle, lower, bandwidth)."""
    if len(closes) < period:
        return {"upper": None, "middle": None, "lower": None, "bandwidth": None}

    window = closes[-period:]
    middle = float(np.mean(window))
    std = float(np.std(window, ddof=1))
    upper = middle + num_std * std
    lower = middle - num_std * std
    bandwidth = ((upper - lower) / middle * 100) if middle != 0 else 0

    return {
        "upper": round(upper, 4),
        "middle": round(middle, 4),
        "lower": round(lower, 4),
        "bandwidth": round(bandwidth, 4),
    }


# ── ATR ──────────────────────────────────────────────────────────────────

def atr(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14,
) -> float | None:
    """Average True Range."""
    if len(closes) < period + 1:
        return None

    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1]),
        ),
    )
    # Wilder's smoothing
    atr_val = float(np.mean(tr[:period]))
    for i in range(period, len(tr)):
        atr_val = (atr_val * (period - 1) + float(tr[i])) / period
    return round(atr_val, 6)


# ── OBV ──────────────────────────────────────────────────────────────────

def obv(closes: np.ndarray, volumes: np.ndarray) -> dict[str, float | None]:
    """On-Balance Volume (current value + trend)."""
    if len(closes) < 2:
        return {"obv": None, "obv_trend": None}

    obv_arr = np.zeros(len(closes))
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv_arr[i] = obv_arr[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            obv_arr[i] = obv_arr[i - 1] - volumes[i]
        else:
            obv_arr[i] = obv_arr[i - 1]

    current = float(obv_arr[-1])
    # Trend: compare last 5 OBV values
    if len(obv_arr) >= 5:
        recent = obv_arr[-5:]
        trend = "rising" if recent[-1] > recent[0] else "falling" if recent[-1] < recent[0] else "flat"
    else:
        trend = "unknown"

    return {"obv": round(current, 2), "obv_trend": trend}


# ── Realized Volatility ─────────────────────────────────────────────────

def realized_volatility(closes: np.ndarray, period: int = 20) -> float | None:
    """Annualized realized volatility from log returns."""
    if len(closes) < period + 1:
        return None
    log_returns = np.diff(np.log(closes[-period - 1:]))
    # Annualize: sqrt(365 * 24) for hourly, sqrt(365*24*4) for 15m
    vol = float(np.std(log_returns, ddof=1))
    return round(vol * 100, 4)  # percentage


# ── All-in-one ───────────────────────────────────────────────────────────

def compute_all(candles: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute all technical indicators from OHLCV candle data.

    Parameters
    ----------
    candles:
        List of dicts with keys: open/o, high/h, low/l, close/c, volume/v

    Returns
    -------
    Dict with all indicator values.
    """
    if not candles or len(candles) < 2:
        return {"error": "insufficient data", "data_points": len(candles) if candles else 0}

    arr = _to_arrays(candles)
    c, h, l, v = arr["close"], arr["high"], arr["low"], arr["volume"]

    return {
        "data_points": len(candles),
        "latest_close": round(float(c[-1]), 4),
        "sma": {
            "sma_7": round(sma(c, 7), 4) if sma(c, 7) is not None else None,
            "sma_25": round(sma(c, 25), 4) if sma(c, 25) is not None else None,
            "sma_99": round(sma(c, 99), 4) if sma(c, 99) is not None else None,
        },
        "ema": {
            "ema_9": round(ema(c, 9), 4) if ema(c, 9) is not None else None,
            "ema_21": round(ema(c, 21), 4) if ema(c, 21) is not None else None,
        },
        "rsi_14": round(rsi(c, 14), 2) if rsi(c, 14) is not None else None,
        "macd": macd(c),
        "bollinger_bands": bollinger_bands(c),
        "atr_14": atr(h, l, c, 14),
        "obv": obv(c, v),
        "realized_volatility": realized_volatility(c),
    }
