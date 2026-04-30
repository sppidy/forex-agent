"""Strategy Engine — maps pairs to strategies with specific trading windows.

Each pair can have its own strategy and trading hours.
The engine checks the time window before running a strategy.
"""

import os
import json
from datetime import datetime, time, timedelta, timezone
from dataclasses import dataclass
from logger import logger

IST = timezone(timedelta(hours=5, minutes=30))
ET = timezone(timedelta(hours=-4))
UTC = timezone.utc

# ── Available strategies ──
# Each strategy module must implement: analyze_pair(symbol, df_15m) -> SweepSignal | None

STRATEGY_MODULES = {
    "ict_asian_sweep": "forex_strategy",       # AH/AL sweep + CISD + Fib 50%
    "london_breakout": "london_breakout",       # Pre-London range breakout
    "killzone_reversal": "killzone_reversal",   # ICT kill zone reversal
}


@dataclass
class PairConfig:
    symbol: str
    strategy: str               # Strategy name from STRATEGY_MODULES
    start_time: time            # Trading window start (in the specified timezone)
    end_time: time              # Trading window end
    tz_name: str = "IST"        # "IST", "ET", "UTC"
    timeframe: str = "15m"      # Candle timeframe to use
    enabled: bool = True


# ── Default pair configurations ──
# Can be overridden via strategy_config.json

DEFAULT_PAIR_CONFIGS: list[dict] = [
    # EUR/USD: ICT Asian Sweep, 11:30 AM - 2:30 PM IST (London/NY overlap)
    {"symbol": "EURUSD=X", "strategy": "ict_asian_sweep",
     "start_time": "11:30", "end_time": "14:30", "tz": "IST"},

    # GBP/USD: ICT Asian Sweep, 1:00 PM - 5:30 PM IST (London afternoon + NY morning)
    {"symbol": "GBPUSD=X", "strategy": "ict_asian_sweep",
     "start_time": "13:00", "end_time": "17:30", "tz": "IST"},

    # USD/JPY: London Breakout, 1:00 PM - 4:00 PM IST (London open)
    {"symbol": "USDJPY=X", "strategy": "london_breakout",
     "start_time": "13:00", "end_time": "16:00", "tz": "IST"},

    # USD/CHF: ICT Asian Sweep, 1:30 PM - 5:00 PM IST
    {"symbol": "USDCHF=X", "strategy": "ict_asian_sweep",
     "start_time": "13:30", "end_time": "17:00", "tz": "IST"},

    # AUD/USD: ICT Asian Sweep, 5:30 AM - 9:30 AM IST (Sydney/Tokyo overlap)
    {"symbol": "AUDUSD=X", "strategy": "ict_asian_sweep",
     "start_time": "05:30", "end_time": "09:30", "tz": "IST"},

    # USD/CAD: Kill Zone Reversal, 6:30 PM - 10:30 PM IST (NY session)
    {"symbol": "USDCAD=X", "strategy": "killzone_reversal",
     "start_time": "18:30", "end_time": "22:30", "tz": "IST"},

    # NZD/USD: ICT Asian Sweep, 5:30 AM - 8:30 AM IST (Sydney session)
    {"symbol": "NZDUSD=X", "strategy": "ict_asian_sweep",
     "start_time": "05:30", "end_time": "08:30", "tz": "IST"},

    # Cross pairs: ICT Asian Sweep during London session
    {"symbol": "EURGBP=X", "strategy": "ict_asian_sweep",
     "start_time": "13:00", "end_time": "17:00", "tz": "IST"},
    {"symbol": "EURJPY=X", "strategy": "ict_asian_sweep",
     "start_time": "13:00", "end_time": "17:00", "tz": "IST"},
    {"symbol": "GBPJPY=X", "strategy": "ict_asian_sweep",
     "start_time": "13:00", "end_time": "18:00", "tz": "IST"},
    {"symbol": "AUDJPY=X", "strategy": "ict_asian_sweep",
     "start_time": "05:30", "end_time": "09:30", "tz": "IST"},
    {"symbol": "EURAUD=X", "strategy": "ict_asian_sweep",
     "start_time": "13:00", "end_time": "17:00", "tz": "IST"},

    # Commodities: Kill Zone Reversal during NY session
    {"symbol": "GC=F", "strategy": "killzone_reversal",
     "start_time": "18:30", "end_time": "23:00", "tz": "IST"},
    {"symbol": "SI=F", "strategy": "killzone_reversal",
     "start_time": "18:30", "end_time": "23:00", "tz": "IST"},
]


def _parse_time(t: str) -> time:
    parts = t.split(":")
    return time(int(parts[0]), int(parts[1]))


def _get_tz(tz_name: str) -> timezone:
    return {"IST": IST, "ET": ET, "UTC": UTC}.get(tz_name, IST)


def _load_configs() -> list[PairConfig]:
    """Load pair configs from JSON override or defaults."""
    import config as fx_config
    config_file = os.path.join(fx_config.PROJECT_DIR, "strategy_config.json")

    configs_raw = DEFAULT_PAIR_CONFIGS
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                configs_raw = json.load(f)
            logger.info(f"  [STRATEGY] Loaded {len(configs_raw)} pair configs from strategy_config.json")
        except Exception as e:
            logger.warning(f"  [STRATEGY] Failed to load strategy_config.json: {e}, using defaults")

    configs = []
    for c in configs_raw:
        configs.append(PairConfig(
            symbol=c["symbol"],
            strategy=c["strategy"],
            start_time=_parse_time(c["start_time"]),
            end_time=_parse_time(c["end_time"]),
            tz_name=c.get("tz", "IST"),
            timeframe=c.get("timeframe", "15m"),
            enabled=c.get("enabled", True),
        ))
    return configs


def is_in_trading_window(cfg: PairConfig) -> bool:
    """Check if the current time is within the pair's trading window."""
    tz = _get_tz(cfg.tz_name)
    now = datetime.now(tz).time()

    if cfg.start_time <= cfg.end_time:
        return cfg.start_time <= now <= cfg.end_time
    else:
        # Overnight window (e.g., 22:00 - 02:00)
        return now >= cfg.start_time or now <= cfg.end_time


def _get_strategy_fn(strategy_name: str):
    """Dynamically load a strategy's analyze_pair function."""
    module_name = STRATEGY_MODULES.get(strategy_name)
    if not module_name:
        return None
    import importlib
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, "analyze_pair", None)
    except Exception as e:
        logger.warning(f"  [STRATEGY] Failed to load {strategy_name}: {e}")
        return None


def scan_all_pairs(get_data_fn) -> list[dict]:
    """Run the correct strategy for each pair based on config and time window.

    Returns list of signal dicts for all pairs.
    """
    configs = _load_configs()
    signals = []

    for cfg in configs:
        if not cfg.enabled:
            signals.append({
                "symbol": cfg.symbol, "signal": "HOLD", "confidence": 0,
                "price": 0, "reason": "Pair disabled in config",
                "strategy": cfg.strategy, "in_window": False,
            })
            continue

        in_window = is_in_trading_window(cfg)
        tz = _get_tz(cfg.tz_name)
        now_str = datetime.now(tz).strftime("%H:%M")
        window_str = f"{cfg.start_time.strftime('%H:%M')}-{cfg.end_time.strftime('%H:%M')} {cfg.tz_name}"

        if not in_window:
            # Outside trading window — fetch price but no signal
            try:
                df = get_data_fn(cfg.symbol, period="1d", interval="15m")
                price = float(df["Close"].iloc[-1]) if not df.empty else 0
            except Exception:
                price = 0
            signals.append({
                "symbol": cfg.symbol, "signal": "HOLD", "confidence": 0,
                "price": price,
                "reason": f"Outside window ({window_str}). Now: {now_str} {cfg.tz_name}",
                "strategy": cfg.strategy, "in_window": False,
                "trading_window": window_str,
            })
            continue

        # In trading window — run the strategy
        analyze_fn = _get_strategy_fn(cfg.strategy)
        if not analyze_fn:
            signals.append({
                "symbol": cfg.symbol, "signal": "HOLD", "confidence": 0,
                "price": 0, "reason": f"Strategy '{cfg.strategy}' not found",
                "strategy": cfg.strategy, "in_window": True,
            })
            continue

        try:
            df = get_data_fn(cfg.symbol, period="5d", interval=cfg.timeframe)
            if df.empty or len(df) < 50:
                signals.append({
                    "symbol": cfg.symbol, "signal": "HOLD", "confidence": 0,
                    "price": 0, "reason": "Insufficient data",
                    "strategy": cfg.strategy, "in_window": True,
                    "trading_window": window_str,
                })
                continue

            result = analyze_fn(cfg.symbol, df)
            if result:
                signals.append({
                    "symbol": result.symbol,
                    "signal": result.signal,
                    "confidence": result.confidence,
                    "price": result.price,
                    "reason": result.reason,
                    "stop_loss": result.stop_loss,
                    "target": result.target,
                    "position_size_pct": min(result.confidence * 0.05, 0.05),
                    "asian_high": getattr(result, "asian_high", None),
                    "asian_low": getattr(result, "asian_low", None),
                    "fib_50": getattr(result, "fib_50", None),
                    "strategy": cfg.strategy, "in_window": True,
                    "trading_window": window_str,
                })
            else:
                price = float(df["Close"].iloc[-1])
                # Get Asian range info for context
                from forex_strategy import _get_asian_range
                asian = _get_asian_range(df)
                signals.append({
                    "symbol": cfg.symbol, "signal": "HOLD", "confidence": 0,
                    "price": price,
                    "reason": f"No {cfg.strategy} setup. AH:{asian.high:.5f} AL:{asian.low:.5f}" if asian else f"No {cfg.strategy} setup",
                    "asian_high": asian.high if asian else None,
                    "asian_low": asian.low if asian else None,
                    "strategy": cfg.strategy, "in_window": True,
                    "trading_window": window_str,
                })
        except Exception as e:
            logger.warning(f"  [STRATEGY] Error on {cfg.symbol}: {e}")
            signals.append({
                "symbol": cfg.symbol, "signal": "HOLD", "confidence": 0,
                "price": 0, "reason": f"Error: {str(e)[:80]}",
                "strategy": cfg.strategy, "in_window": True,
            })

    return signals


def get_all_configs() -> list[dict]:
    """Return current strategy configs for the API."""
    configs = _load_configs()
    return [
        {
            "symbol": c.symbol,
            "strategy": c.strategy,
            "start_time": c.start_time.strftime("%H:%M"),
            "end_time": c.end_time.strftime("%H:%M"),
            "timezone": c.tz_name,
            "timeframe": c.timeframe,
            "enabled": c.enabled,
            "in_window": is_in_trading_window(c),
        }
        for c in configs
    ]
