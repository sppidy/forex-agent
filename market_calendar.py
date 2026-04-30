"""Forex market calendar — 24/5 session logic (Sun 5PM ET - Fri 5PM ET)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from logger import logger

# Forex sessions (in ET / US Eastern)
ET = timezone(timedelta(hours=-4))  # EDT (summer), adjust for EST if needed

# Market hours: Sunday 5:00 PM ET to Friday 5:00 PM ET
MARKET_OPEN_DAY = 6   # Sunday
MARKET_OPEN_TIME = time(hour=17, minute=0)   # 5:00 PM ET Sunday
MARKET_CLOSE_DAY = 4  # Friday
MARKET_CLOSE_TIME = time(hour=17, minute=0)  # 5:00 PM ET Friday

# Trading sessions (ET)
SESSIONS = {
    "Sydney":  (time(17, 0), time(2, 0)),   # 5 PM - 2 AM ET
    "Tokyo":   (time(19, 0), time(4, 0)),   # 7 PM - 4 AM ET
    "London":  (time(3, 0),  time(12, 0)),  # 3 AM - 12 PM ET
    "NewYork": (time(8, 0),  time(17, 0)),  # 8 AM - 5 PM ET
}


def now_et() -> datetime:
    """Return current timestamp in ET."""
    return datetime.now(ET)


# Alias for compatibility with NSE agent interface
def now_ist() -> datetime:
    """Alias — returns ET time for forex."""
    return now_et()


def is_market_trading_day(day: date | None = None) -> bool:
    """Forex trades 24/5: Sunday 5PM ET through Friday 5PM ET."""
    now = now_et()
    if day is None:
        day = now.date()

    weekday = day.weekday()  # Mon=0, Sun=6

    # Saturday is always closed
    if weekday == 5:
        return False

    # Sunday: only open after 5 PM ET
    if weekday == 6:
        if day == now.date():
            return now.time() >= MARKET_OPEN_TIME
        return True  # Future Sundays — assume open in evening

    # Friday: only open until 5 PM ET
    if weekday == 4:
        if day == now.date():
            return now.time() <= MARKET_CLOSE_TIME
        return True

    # Mon-Thu: always open
    return True


def is_market_open() -> bool:
    """Check if forex market is currently open."""
    now = now_et()
    weekday = now.weekday()

    if weekday == 5:  # Saturday
        return False
    if weekday == 6:  # Sunday
        return now.time() >= MARKET_OPEN_TIME
    if weekday == 4:  # Friday
        return now.time() <= MARKET_CLOSE_TIME
    return True  # Mon-Thu: 24h


def get_active_sessions() -> list[str]:
    """Return list of currently active forex sessions."""
    now = now_et()
    current_time = now.time()
    active = []
    for name, (start, end) in SESSIONS.items():
        if start < end:
            if start <= current_time <= end:
                active.append(name)
        else:
            # Overnight session (e.g., Sydney 5PM-2AM)
            if current_time >= start or current_time <= end:
                active.append(name)
    return active


def time_to_market_open() -> timedelta | None:
    """Time remaining until forex market opens. None if already open."""
    if is_market_open():
        return None
    now = now_et()
    # Market opens Sunday 5 PM ET
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now.time() < MARKET_OPEN_TIME:
        next_open = now.replace(hour=17, minute=0, second=0, microsecond=0)
    else:
        if days_until_sunday == 0:
            days_until_sunday = 7
        next_open = (now + timedelta(days=days_until_sunday)).replace(
            hour=17, minute=0, second=0, microsecond=0
        )
    return next_open - now
