"""Pure conversion of Massive SDK responses into (price, seconds, reference) quotes."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from massive.exceptions import BadResponse
from massive.rest.models import GroupedDailyAgg, TickerSnapshot

NY = ZoneInfo("America/New_York")
EOD_MIN_INTERVAL = 900
HISTORY_DAYS = 180
# EOD mode (free tier, 5 calls/min): at most EOD_CALLS calls in any RATE_WINDOW seconds.
EOD_CALLS = 5
RATE_WINDOW = 61

Quote = tuple[float, float, float | None]


def not_authorized(e: Exception) -> bool:
    """True for a plan-entitlement 403 (also today-before-close on grouped bars)."""
    return isinstance(e, BadResponse) and "NOT_AUTHORIZED" in str(e)


def snapshot_quote(snap: TickerSnapshot) -> Quote | None:
    """Best price with its source time; None when no price or no timestamp."""
    prev = snap.prev_day.close if snap.prev_day and snap.prev_day.close else None
    updated = snap.updated / 1e9 if snap.updated else None
    trade = snap.last_trade
    if trade and trade.price and trade.sip_timestamp:
        return trade.price, trade.sip_timestamp / 1e9, prev
    if snap.min and snap.min.close and snap.min.timestamp:
        return snap.min.close, snap.min.timestamp / 1e3, prev
    price = (snap.day.close if snap.day and snap.day.close else None) or prev
    return (price, updated, prev) if price and updated else None


def bar_quote(bar) -> Quote:
    """Close, bar time in seconds, and the open as the day-change reference."""
    return bar.close, bar.timestamp / 1e3, bar.open


async def latest_grouped_bars(fetch, today: date, tries: int = 5) -> dict[str, GroupedDailyAgg]:
    """Bars for the newest NY trading day the plan may read, stepping back over 403/empty days.

    `fetch` is an async callable taking an ISO date and returning that day's grouped bars.
    """
    day = today
    for _ in range(tries):
        try:
            bars = await fetch(day.isoformat())
        except BadResponse as e:
            if not not_authorized(e):
                raise
            bars = []
        if bars:
            return {b.ticker: b for b in bars if b.close}
        day -= timedelta(days=1)
    return {}


def history_window(today: date) -> tuple[str, str]:
    """ISO (start, end) dates covering the last HISTORY_DAYS days."""
    return (today - timedelta(days=HISTORY_DAYS)).isoformat(), today.isoformat()


def daily_points(aggs) -> list[dict]:
    """Ascending {time, value} points (seconds, close) from daily bars; skips bars lacking either."""
    points = [
        {"time": int(a.timestamp // 1000), "value": round(a.close, 2)}
        for a in aggs
        if a.close and a.timestamp
    ]
    return sorted(points, key=lambda p: p["time"])
