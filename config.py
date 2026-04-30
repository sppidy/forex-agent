"""Configuration for the Forex paper trading agent."""

import json
import os
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Starting capital in USD
INITIAL_CAPITAL = 100_000.0
MARKET_INDEX = "DX-Y.NYB"  # US Dollar Index for regime detection

# Forex watchlist — major pairs, crosses, and indices
WATCHLIST = [
    # ── Major pairs ──
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "USDCHF=X",
    "AUDUSD=X",
    "USDCAD=X",
    "NZDUSD=X",
    # ── Cross pairs ──
    "EURGBP=X",
    "EURJPY=X",
    "GBPJPY=X",
    "AUDJPY=X",
    "EURAUD=X",
    # ── Commodities (futures format for yfinance) ──
    "GC=F",          # Gold
    "SI=F",          # Silver
]

CURRENCY_SYMBOL = "$"

# Trading parameters — tighter for forex
MAX_POSITION_SIZE_PCT = 0.05   # 5% per pair
MAX_OPEN_POSITIONS = 10
BROKERAGE_PER_ORDER = 0.0     # Paper trading
SLIPPAGE_PCT = 0.0002         # 2 pips simulated slippage

# Strategy parameters (RSI + EMA)
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
EMA_SHORT = 9
EMA_LONG = 21
STOP_LOSS_PCT = 0.005         # 50 pips
TAKE_PROFIT_PCT = 0.01        # 100 pips
DYNAMIC_TRAILING_ENABLED = True
MIN_STOP_LOSS_PCT = 0.002     # 20 pips
MAX_STOP_LOSS_PCT = 0.015     # 150 pips
MIN_TAKE_PROFIT_PCT = 0.004   # 40 pips
MAX_TAKE_PROFIT_PCT = 0.03    # 300 pips
TRAILING_CONFIDENCE_SCALE = 0.6
TRAILING_PROFIT_LOCK_SCALE = 0.35

# Capital utilization
CAPITAL_DEPLOYMENT_TARGET_PCT = 0.8
CAPITAL_UTILIZATION_MIN_BET_PCT = 0.02

# Data settings
DATA_INTERVAL = "15m"
BACKTEST_DAYS = 60

# ── Hot-reload from config_overrides.json ─────────────────────
_OVERRIDES_FILE = os.path.join(PROJECT_DIR, "config_overrides.json")
_RELOADABLE = {
    "MAX_POSITION_SIZE_PCT", "MAX_OPEN_POSITIONS",
    "STOP_LOSS_PCT", "TAKE_PROFIT_PCT", "DYNAMIC_TRAILING_ENABLED",
    "MIN_STOP_LOSS_PCT", "MAX_STOP_LOSS_PCT", "MIN_TAKE_PROFIT_PCT",
    "MAX_TAKE_PROFIT_PCT", "RSI_OVERSOLD", "RSI_OVERBOUGHT",
    "CAPITAL_DEPLOYMENT_TARGET_PCT", "CAPITAL_UTILIZATION_MIN_BET_PCT",
    "DATA_INTERVAL", "BACKTEST_DAYS",
}
_last_reload: float = 0
_RELOAD_INTERVAL = 60


def reload_overrides(force: bool = False) -> list[str]:
    global _last_reload
    now = time.time()
    if not force and (now - _last_reload) < _RELOAD_INTERVAL:
        return []
    _last_reload = now
    if not os.path.exists(_OVERRIDES_FILE):
        return []
    try:
        with open(_OVERRIDES_FILE, "r") as f:
            overrides = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    changed = []
    mod = globals()
    for key, value in overrides.items():
        if key in _RELOADABLE and mod.get(key) != value:
            mod[key] = value
            changed.append(key)
    return changed
