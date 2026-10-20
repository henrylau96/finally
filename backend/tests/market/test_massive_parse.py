from datetime import date

import pytest
from massive.exceptions import BadResponse
from massive.rest.models import Agg, GroupedDailyAgg, TickerSnapshot

from app.market.massive_parse import (
    bar_quote,
    daily_points,
    history_window,
    latest_grouped_bars,
    not_authorized,
    snapshot_quote,
)

NOT_AUTH = '{"status":"NOT_AUTHORIZED","message":"You are not entitled to this data."}'


class GroupedClient:
    """Returns grouped bars per ISO date; exceptions are raised."""

    def __init__(self, by_date):
        self.by_date = by_date
        self.calls = []

    async def fetch(self, day):
        self.calls.append(day)
        value = self.by_date.get(day, [])
        if isinstance(value, Exception):
            raise value
        return value


def snap(**data):
    return TickerSnapshot.from_dict({"ticker": "AAPL", **data})


def test_quote_prefers_last_trade():
    """Last trade wins, with its ns timestamp in seconds and the prev close as reference."""
    s = snap(lastTrade={"p": 190.5, "t": 1760790000_000000000}, min={"c": 189.0, "t": 1}, prevDay={"c": 188.0})
    assert snapshot_quote(s) == (190.5, 1760790000.0, 188.0)


def test_quote_falls_back_to_minute_bar():
    """Without a last trade the minute bar close is used, ms to seconds."""
    s = snap(min={"c": 189.0, "t": 1760790000000}, prevDay={"c": 188.0})
    assert snapshot_quote(s) == (189.0, 1760790000.0, 188.0)


def test_quote_day_close_uses_updated_timestamp():
    """Day close carries no time, so the snapshot updated time (ns) is used."""
    s = snap(day={"c": 191.0}, updated=1760790000_000000000)
    assert snapshot_quote(s) == (191.0, 1760790000.0, None)


def test_quote_prev_day_only_uses_updated():
    """Prev close alone is a price, timed by the snapshot updated field."""
    s = snap(prevDay={"c": 188.0}, updated=1760790000_000000000)
    assert snapshot_quote(s) == (188.0, 1760790000.0, 188.0)


def test_quote_none_without_timestamp():
    """No source time means no quote, never an invented one."""
    assert snapshot_quote(snap(day={"c": 191.0})) is None


def test_quote_skips_zero_minute_bar():
    """A pre-market zero minute bar falls through to the day close."""
    s = snap(min={"c": 0, "t": 0}, day={"c": 191.0}, updated=1760790000_000000000)
    assert snapshot_quote(s) == (191.0, 1760790000.0, None)


def test_bar_quote_timestamp():
    """A bar gives close, NY-midnight session time in seconds, and open as reference."""
    bar = GroupedDailyAgg.from_dict({"T": "AAPL", "o": 188.0, "c": 190.2, "t": 1760731200000})
    assert bar_quote(bar) == (190.2, 1760673600.0, 188.0)


async def test_grouped_steps_back_over_403_and_weekend():
    """Today 403 and two empty days are skipped; the third day's bars are keyed by ticker."""
    bars = [
        GroupedDailyAgg.from_dict({"T": "AAPL", "o": 1.0, "c": 2.0, "t": 1}),
        GroupedDailyAgg.from_dict({"T": "MSFT", "o": 3.0, "c": 4.0, "t": 1}),
    ]
    client = GroupedClient({"2026-10-19": BadResponse(NOT_AUTH), "2026-10-16": bars})
    result = await latest_grouped_bars(client.fetch, date(2026, 10, 19))
    assert set(result) == {"AAPL", "MSFT"}
    assert client.calls == ["2026-10-19", "2026-10-18", "2026-10-17", "2026-10-16"]


async def test_grouped_gives_up_after_five():
    """Five empty days give an empty dict."""
    client = GroupedClient({})
    assert await latest_grouped_bars(client.fetch, date(2026, 10, 19)) == {}
    assert len(client.calls) == 5


async def test_grouped_other_bad_response_raises():
    """A BadResponse that is not an entitlement error propagates."""
    client = GroupedClient({"2026-10-19": BadResponse('{"status":"ERROR"}')})
    with pytest.raises(BadResponse):
        await latest_grouped_bars(client.fetch, date(2026, 10, 19))


def test_not_authorized_detection():
    """Only a BadResponse whose body says NOT_AUTHORIZED counts."""
    assert not_authorized(BadResponse(NOT_AUTH))
    assert not not_authorized(BadResponse('{"status":"ERROR"}'))
    assert not not_authorized(RuntimeError("NOT_AUTHORIZED"))


def test_daily_points_sorted_rounded_and_filtered():
    """Seconds, 2 dp, ascending; bars without close or timestamp are skipped."""
    aggs = [
        Agg.from_dict({"c": 190.123, "t": 1760500000000}),
        Agg.from_dict({"t": 1760450000000}),
        Agg.from_dict({"c": 188.0}),
        Agg.from_dict({"c": 188.0, "t": 1760400000000}),
    ]
    assert daily_points(aggs) == [
        {"time": 1760400000, "value": 188.0},
        {"time": 1760500000, "value": 190.12},
    ]


def test_history_window_is_180_days():
    """The window ends today and starts 180 days earlier."""
    assert history_window(date(2026, 10, 19)) == ("2026-04-22", "2026-10-19")


def test_bar_quote_matches_daily_points_time():
    """Grouped bar time equals the get_aggs day-bar time of the same session (WR-05)."""
    grouped = GroupedDailyAgg.from_dict({"T": "AAPL", "o": 340.0, "c": 343.46, "t": 1792180800000})
    agg = Agg.from_dict({"o": 340.0, "c": 343.46, "t": 1792123200000})
    assert bar_quote(grouped)[1] == daily_points([agg])[0]["time"] == 1792123200
