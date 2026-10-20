import asyncio
from datetime import date

import pytest
from massive.exceptions import BadResponse
from massive.rest.models import Agg, GroupedDailyAgg, PreviousCloseAgg, TickerSnapshot

from app.market import MassiveDataSource, PriceCache
from app.market import massive_source

NOT_AUTH = '{"status":"NOT_AUTHORIZED","message":"You are not entitled to this data."}'
TODAY = "2026-10-19"
BAR_T = 1760731200000


class FakeClient:
    """Records calls; each attribute is a value or an exception to raise."""

    def __init__(self, snapshots=None, grouped=None, single=None, prev=None, aggs=None):
        self.aggs = aggs
        self.snapshots, self.grouped, self.single, self.prev = snapshots, grouped or {}, single, prev
        self.calls: list[tuple] = []

    def _ret(self, value):
        if isinstance(value, Exception):
            raise value
        return value

    def get_snapshot_all(self, market_type, tickers=None):
        self.calls.append(("all", market_type, tuple(tickers)))
        return self._ret(self.snapshots)

    def get_snapshot_ticker(self, market_type, ticker):
        self.calls.append(("one", ticker))
        return self._ret(self.single)

    def get_grouped_daily_aggs(self, date, adjusted=None):
        self.calls.append(("grouped", date))
        return self._ret(self.grouped.get(date, []))

    def get_aggs(self, ticker, multiplier, timespan, from_, to, adjusted=None, sort=None, limit=None):
        self.calls.append(("aggs", ticker, multiplier, timespan, from_, to, adjusted, sort))
        return self._ret(self.aggs or [])

    def get_previous_close_agg(self, ticker, adjusted=None):
        self.calls.append(("prev", ticker))
        return self._ret(self.prev or [])


def snapshot(ticker, price, ns, prev):
    return TickerSnapshot.from_dict({"ticker": ticker, "lastTrade": {"p": price, "t": ns}, "prevDay": {"c": prev}})


def bar(ticker, open_, close, cls=GroupedDailyAgg):
    return cls.from_dict({"T": ticker, "o": open_, "c": close, "t": BAR_T})


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """Pin the NY date the source asks for."""
    monkeypatch.setattr(massive_source, "ny_today", lambda: date(2026, 10, 19))


def eod_client(**kwargs):
    grouped = {TODAY: [bar("AAPL", 188.0, 190.2), bar("MSFT", 400.0, 404.0), bar("ZZZZ", 1.0, 2.0)]}
    return FakeClient(snapshots=BadResponse(NOT_AUTH), grouped=grouped, **kwargs)


async def started(client, tickers=("AAPL", "MSFT"), interval=15.0):
    cache = PriceCache()
    source = MassiveDataSource(cache, client, interval)
    await source.start(list(tickers))
    return cache, source


async def test_snapshot_mode_timestamp_and_reference():
    """Snapshot prices carry the source time and day change against the prev close."""
    client = FakeClient(snapshots=[snapshot("AAPL", 190.0, 1760790000_000000000, 200.0)])
    cache, source = await started(client, ["AAPL"])
    u = cache.get("AAPL")
    assert u.timestamp == 1760790000.0
    assert u.day_change_pct == -5.0
    assert client.calls[0] == ("all", "stocks", ("AAPL",))
    assert source._mode == "snapshot"
    await source.stop()


async def test_fallback_to_eod_on_not_authorized():
    """A snapshot 403 switches to EOD; only tracked tickers are cached with bar times."""
    cache, source = await started(eod_client())
    assert source._mode == "eod"
    assert source._interval >= 900
    assert cache.get("AAPL").price == 190.2
    assert cache.get("AAPL").timestamp == BAR_T / 1e3
    assert cache.get("MSFT").day_change_pct == 1.0
    assert cache.get("ZZZZ") is None
    await source.stop()


async def test_eod_poll_does_not_retry_snapshot():
    """Once in EOD mode a poll makes no snapshot call."""
    client = eod_client()
    _, source = await started(client)
    before = len(client.calls)
    await source._poll_once()
    assert all(c[0] != "all" for c in client.calls[before:])
    await source.stop()


async def test_add_ticker_snapshot_fetches_one():
    """In snapshot mode a new ticker is fetched alone before add_ticker returns."""
    client = FakeClient(snapshots=[], single=snapshot("PYPL", 70.0, 1760790000_000000000, 69.0))
    cache, source = await started(client, ["AAPL"])
    await source.add_ticker("PYPL")
    assert client.calls[-1] == ("one", "PYPL")
    assert cache.get("PYPL").price == 70.0
    assert "PYPL" in source.get_tickers()
    await source.stop()


async def test_add_ticker_eod_uses_cached_bar():
    """In EOD mode a ticker present in the grouped bars costs no call."""
    client = eod_client()
    cache, source = await started(client)
    before = len(client.calls)
    await source.add_ticker("ZZZZ")
    assert len(client.calls) == before
    assert cache.get("ZZZZ").price == 2.0
    await source.stop()


async def test_add_ticker_eod_prev_close():
    """In EOD mode a ticker missing from the bars uses its previous close."""
    client = eod_client(prev=[bar("PYPL", 69.0, 70.0, PreviousCloseAgg)])
    cache, source = await started(client)
    await source.add_ticker("PYPL")
    assert client.calls[-1] == ("prev", "PYPL")
    assert cache.get("PYPL").timestamp == BAR_T / 1e3
    await source.stop()


async def test_add_ticker_tracked_is_noop():
    """An already tracked and priced ticker makes no client call."""
    client = FakeClient(snapshots=[snapshot("AAPL", 190.0, 1760790000_000000000, 188.0)])
    _, source = await started(client, ["AAPL"])
    before = len(client.calls)
    await source.add_ticker("AAPL")
    assert len(client.calls) == before
    await source.stop()


async def test_add_ticker_failure_leaves_no_entry():
    """A failed or empty fetch leaves no cache entry and raises nothing."""
    client = FakeClient(snapshots=[], single=BadResponse('{"status":"ERROR"}'))
    cache, source = await started(client, ["AAPL"])
    await source.add_ticker("PYPL")
    assert cache.get("PYPL") is None
    await source.stop()
    cache, source = await started(eod_client())
    await source.add_ticker("QQQQ")
    assert cache.get("QQQQ") is None
    await source.stop()


async def test_add_ticker_empty_start_falls_back_to_eod():
    """A free-tier key started with no tickers still prices a new ticker via EOD."""
    client = FakeClient(single=BadResponse(NOT_AUTH), prev=[bar("PYPL", 69.0, 70.0, PreviousCloseAgg)])
    cache, source = await started(client, [])
    assert client.calls == []
    await source.add_ticker("PYPL")
    price = cache.get("PYPL")
    assert price.price == 70.0
    assert price.timestamp == BAR_T / 1e3
    assert source._mode == "eod"
    assert source._interval >= 900
    assert client.calls[-2:] == [("one", "PYPL"), ("prev", "PYPL")]
    await source.stop()


async def test_remove_ticker_drops_cache():
    """Removing a ticker stops tracking it and clears its price."""
    cache, source = await started(eod_client())
    await source.remove_ticker("AAPL")
    assert "AAPL" not in source.get_tickers()
    assert cache.get("AAPL") is None
    await source.stop()


async def test_poll_survives_errors(caplog):
    """A failing poll is logged and the loop polls again."""
    client = FakeClient(snapshots=[snapshot("AAPL", 190.0, 1760790000_000000000, 188.0)])
    _, source = await started(client, ["AAPL"], interval=0.02)
    client.snapshots = RuntimeError("boom")
    await asyncio.sleep(0.06)
    count = len(client.calls)
    await asyncio.sleep(0.06)
    assert "Massive poll failed" in caplog.text
    assert len(client.calls) > count
    await source.stop()
    await source.stop()


async def test_bad_response_logs_one_line(caplog):
    """An API error such as an unknown key is logged as one line, with no traceback."""
    client = FakeClient(snapshots=BadResponse('{"status":"ERROR","error":"Unknown API Key"}'))
    _, source = await started(client, ["AAPL"])
    client.single = client.snapshots
    await source.add_ticker("PYPL")
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 2
    assert all(r.exc_info is None and "Unknown API Key" in r.getMessage() for r in errors)
    await source.stop()


async def test_unchanged_poll_keeps_cache_version():
    """A poll that returns the same quotes does not bump the cache version."""
    cache, source = await started(eod_client())
    version = cache.version
    await source._poll_once()
    assert cache.version == version
    await source.stop()


async def test_add_ticker_retries_after_failed_fetch():
    """A tracked ticker left unpriced by a failed fetch is fetched again on the next add."""
    client = FakeClient(snapshots=[], single=RuntimeError("boom"))
    cache, source = await started(client, ["AAPL"])
    await source.add_ticker("PYPL")
    assert cache.get("PYPL") is None
    client.single = snapshot("PYPL", 70.0, 1760790000_000000000, 69.0)
    await source.add_ticker("PYPL")
    assert cache.get("PYPL").price == 70.0
    await source.stop()


def history_source(**kwargs):
    client = FakeClient(**kwargs)
    return MassiveDataSource(PriceCache(), client), client


def agg(close, t):
    return Agg.from_dict({"c": close, "t": t})


AGGS = [agg(190.0, 1760400000000), agg(191.5, 1760486400000)]
POINTS = [{"time": 1760400000, "value": 190.0}, {"time": 1760486400, "value": 191.5}]


async def test_history_returns_points_with_exact_call():
    """Daily bars are requested for the 180-day window and parsed."""
    source, client = history_source(aggs=AGGS)
    assert await source.history("AAPL") == POINTS
    assert client.calls == [("aggs", "AAPL", 1, "day", "2026-04-22", "2026-10-19", True, "asc")]


async def test_history_cached_per_ticker_per_day(monkeypatch):
    """Same ticker same day hits the cache; other tickers and the next day fetch."""
    source, client = history_source(aggs=AGGS)
    await source.history("AAPL")
    await source.history("AAPL")
    assert len(client.calls) == 1
    await source.history("MSFT")
    assert len(client.calls) == 2
    monkeypatch.setattr(massive_source, "ny_today", lambda: date(2026, 10, 20))
    await source.history("AAPL")
    assert len(client.calls) == 3


async def test_history_failure_returns_empty_and_retries():
    """An API error returns [] and is not cached."""
    source, client = history_source(aggs=BadResponse(NOT_AUTH))
    assert await source.history("AAPL") == []
    assert await source.history("AAPL") == []
    assert len(client.calls) == 2


async def test_history_empty_success_is_cached():
    """A successful empty response is cached."""
    source, client = history_source(aggs=[])
    assert await source.history("AAPL") == []
    assert await source.history("AAPL") == []
    assert len(client.calls) == 1
