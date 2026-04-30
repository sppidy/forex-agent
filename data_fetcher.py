"""Fetch forex market data using yfinance."""

import math
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from logger import logger


def _clean_price(value) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(price) or price <= 0:
        return None
    return price


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: logger.warning(f"Retrying yfinance API call. Attempt {retry_state.attempt_number}")
)
def get_historical_data(symbol: str, period: str = "60d", interval: str = "1d") -> pd.DataFrame:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return df
        df.index = df.index.tz_localize(None) if df.index.tz else df.index
        return df
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        raise e


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: logger.warning(f"Retrying yfinance API call. Attempt {retry_state.attempt_number}")
)
def get_live_price(symbol: str) -> float | None:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        live = _clean_price(info.get("lastPrice") if info is not None else None)
        if live is not None:
            return live
        hist = ticker.history(period="1d")
        if not hist.empty:
            return _clean_price(hist["Close"].iloc[-1])
        return None
    except Exception as e:
        logger.error(f"Error fetching live price for {symbol}: {e}")
        raise e


def get_watchlist_prices(watchlist: list[str] | None = None) -> dict[str, float]:
    if watchlist is None:
        watchlist = config.WATCHLIST
    prices = {}
    for symbol in watchlist:
        try:
            price = get_live_price(symbol)
            if price is not None:
                prices[symbol] = price
        except Exception as e:
            logger.warning(f"Skipping {symbol}: {e}")
    return prices


def get_market_regime() -> str:
    """Detect regime using DXY (US Dollar Index)."""
    try:
        df = get_historical_data(config.MARKET_INDEX, period="1y", interval="1d")
        if df.empty or len(df) < 200:
            return "NEUTRAL"
        current_price = df["Close"].iloc[-1]
        sma_50 = df["Close"].rolling(window=50).mean().iloc[-1]
        sma_200 = df["Close"].rolling(window=200).mean().iloc[-1]
        # For DXY: strong dollar = BULL, weak dollar = BEAR
        if current_price > sma_50 and sma_50 > sma_200:
            return "BULL"
        elif current_price < sma_200:
            return "BEAR"
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"Error detecting market regime: {e}")
        return "NEUTRAL"
