"""Pure conversion of Massive SDK responses into (price, seconds, reference) quotes."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from massive.exceptions import BadResponse
from massive.rest.models import GroupedDailyAgg, TickerSnapshot

NY = ZoneInfo("America/New_York")
EOD_MIN_INTERVAL = 900

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


def latest_grouped_bars(client, today: date, tries: int = 5) -> dict[str, GroupedDailyAgg]:
    """Bars for the newest NY trading day the plan may read, stepping back over 403/empty days."""
    day = today
    for _ in range(tries):
        try:
            bars = client.get_grouped_daily_aggs(day.isoformat(), adjusted=True)
        except BadResponse as e:
            if not not_authorized(e):
                raise
            bars = []
        if bars:
            return {b.ticker: b for b in bars if b.close}
        day -= timedelta(days=1)
    return {}
