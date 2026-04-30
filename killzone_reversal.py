"""ICT Kill Zone Reversal Strategy.

Rules:
1. Identify the kill zone (NY session 8 AM - 11 AM ET)
2. Wait for a liquidity sweep (new high/low of the day)
3. Look for immediate reversal (engulfing candle or strong rejection wick)
4. Enter on the reversal with SL beyond the sweep point
5. TP at the opposite side of the kill zone range
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta, timezone
from dataclasses import dataclass
from logger import logger

ET = timezone(timedelta(hours=-4))

# Kill zones (ET)
NY_KILLZONE_START = time(8, 0)
NY_KILLZONE_END = time(11, 0)
LONDON_KILLZONE_START = time(3, 0)
LONDON_KILLZONE_END = time(5, 0)


@dataclass
class SweepSignal:
    symbol: str
    signal: str
    confidence: float
    price: float
    reason: str
    stop_loss: float | None = None
    target: float | None = None


def _get_day_range(df: pd.DataFrame) -> tuple[float, float] | None:
    """Get today's high and low before the kill zone."""
    if df.empty:
        return None

    now = datetime.now(ET)
    day_start = datetime.combine(now.date(), time(0, 0), tzinfo=ET)

    try:
        idx = df.index
        if hasattr(idx, 'tz') and idx.tz is not None:
            idx = idx.tz_convert(ET)
        mask = idx >= day_start
        today = df[mask]
    except Exception:
        today = df.tail(40)

    if today.empty:
        return None

    return float(today["High"].max()), float(today["Low"].min())


def _is_engulfing(prev_open, prev_close, curr_open, curr_close) -> str | None:
    """Detect engulfing candle pattern."""
    prev_body = abs(prev_close - prev_open)
    curr_body = abs(curr_close - curr_open)

    if curr_body < prev_body * 0.5:
        return None

    # Bullish engulfing
    if prev_close < prev_open and curr_close > curr_open:
        if curr_close > prev_open and curr_open <= prev_close:
            return "bullish"

    # Bearish engulfing
    if prev_close > prev_open and curr_close < curr_open:
        if curr_close < prev_open and curr_open >= prev_close:
            return "bearish"

    return None


def _has_rejection_wick(high, low, open_p, close, direction: str) -> bool:
    """Check for strong rejection wick (pin bar)."""
    body = abs(close - open_p)
    total_range = high - low
    if total_range <= 0:
        return False

    if direction == "bullish":
        lower_wick = min(open_p, close) - low
        return lower_wick > body * 1.5 and lower_wick > total_range * 0.5

    elif direction == "bearish":
        upper_wick = high - max(open_p, close)
        return upper_wick > body * 1.5 and upper_wick > total_range * 0.5

    return False


def analyze_pair(symbol: str, df: pd.DataFrame) -> SweepSignal | None:
    """Check for kill zone reversal setup."""
    if df.empty or len(df) < 30:
        return None

    day_range = _get_day_range(df)
    if day_range is None:
        return None

    day_high, day_low = day_range
    day_size = day_high - day_low
    if day_size <= 0:
        return None

    # Check last few candles for sweep + reversal
    lookback = min(10, len(df))
    for i in range(len(df) - lookback, len(df) - 1):
        curr = df.iloc[i + 1]
        prev = df.iloc[i]

        curr_high = float(curr["High"])
        curr_low = float(curr["Low"])
        curr_open = float(curr["Open"])
        curr_close = float(curr["Close"])
        prev_open = float(prev["Open"])
        prev_close = float(prev["Close"])

        # Bearish setup: swept day high, then reversal
        if curr_high >= day_high:
            engulfing = _is_engulfing(prev_open, prev_close, curr_open, curr_close)
            rejection = _has_rejection_wick(curr_high, curr_low, curr_open, curr_close, "bearish")

            if engulfing == "bearish" or rejection:
                current = float(df["Close"].iloc[-1])
                if current < day_high:  # Confirmed reversal
                    confidence = 0.70 if engulfing else 0.60
                    return SweepSignal(
                        symbol=symbol,
                        signal="SELL",
                        confidence=confidence,
                        price=current,
                        reason=f"Kill zone: day high {day_high:.5f} swept, {'engulfing' if engulfing else 'rejection wick'} reversal",
                        stop_loss=round(curr_high * 1.0003, 5),
                        target=round(current - day_size * 0.8, 5),
                    )

        # Bullish setup: swept day low, then reversal
        if curr_low <= day_low:
            engulfing = _is_engulfing(prev_open, prev_close, curr_open, curr_close)
            rejection = _has_rejection_wick(curr_high, curr_low, curr_open, curr_close, "bullish")

            if engulfing == "bullish" or rejection:
                current = float(df["Close"].iloc[-1])
                if current > day_low:
                    confidence = 0.70 if engulfing else 0.60
                    return SweepSignal(
                        symbol=symbol,
                        signal="BUY",
                        confidence=confidence,
                        price=current,
                        reason=f"Kill zone: day low {day_low:.5f} swept, {'engulfing' if engulfing else 'rejection wick'} reversal",
                        stop_loss=round(curr_low * 0.9997, 5),
                        target=round(current + day_size * 0.8, 5),
                    )

    return None
