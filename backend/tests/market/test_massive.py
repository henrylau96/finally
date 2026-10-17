"""Tests for MassiveDataSource, built from real SDK models (not MagicMock)."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from massive import RESTClient
from massive.exceptions import BadResponse
from massive.rest.models import GroupedDailyAgg, TickerSnapshot

from app.market.cache import PriceCache
from app.market.massive_client import (
    MARKET_TZ,
    MassiveDataSource,
    latest_eod_closes,
    snapshot_price,
)

TRADE_NS = 1760790000_000000000
MINUTE_MS = 1760790060_000
NOT_AUTHORIZED = '{"status":"NOT_AUTHORIZED","message":"You are not entitled to this data."}'


def _snap(**fields) -> TickerSnapshot:
    """Build a real TickerSnapshot from Massive JSON keys."""
    return TickerSnapshot.from_dict({"ticker": "AAPL", **fields})


def _developer_snap(ticker: str, price: float) -> TickerSnapshot:
    """Snapshot as returned on plans that include trades."""
    return TickerSnapshot.from_dict(
        {"ticker": ticker, "lastTrade": {"p": price, "t": TRADE_NS}, "prevDay": {"c": 1.0}}
    )


def _bar(ticker: str, close: float) -> GroupedDailyAgg:
    return GroupedDailyAgg.from_dict({"T": ticker, "c": close, "t": MINUTE_MS})


def _source(tickers: list[str] | None = None) -> tuple[MassiveDataSource, PriceCache]:
    cache = PriceCache()
    source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
    source._tickers = tickers or []
    source._client = MagicMock()
    return source, cache


class TestSnapshotPrice:
    """Price extraction fallback chain."""

    def test_last_trade_preferred(self):
        snap = _snap(lastTrade={"p": 190.5, "t": TRADE_NS}, min={"c": 190.4, "t": MINUTE_MS})
        assert snapshot_price(snap) == (190.5, 1760790000.0)

    def test_starter_plan_uses_minute_bar(self):
        snap = _snap(min={"c": 190.4, "t": MINUTE_MS}, day={"c": 190.0}, prevDay={"c": 188.0})
        assert snapshot_price(snap) == (190.4, 1760790060.0)

    def test_day_close_when_no_minute_bar(self):
        assert snapshot_price(_snap(day={"c": 190.0}, prevDay={"c": 188.0})) == (190.0, None)

    def test_premarket_zero_day_uses_prev_day(self):
        snap = _snap(min={"c": 0, "t": 0}, day={"c": 0}, prevDay={"c": 188.0})
        assert snapshot_price(snap) == (188.0, None)

    def test_empty_snapshot_returns_none(self):
        assert snapshot_price(_snap()) is None


class TestLatestEodCloses:
    """Grouped daily bars, stepping back over non-trading days."""

    def test_returns_closes(self):
        client = MagicMock()
        client.get_grouped_daily_aggs.return_value = [_bar("AAPL", 190.0), _bar("MSFT", 420.0)]
        assert latest_eod_closes(client) == {"AAPL": 190.0, "MSFT": 420.0}

    def test_steps_back_over_weekend(self):
        client = MagicMock()
        client.get_grouped_daily_aggs.side_effect = [[], [], [_bar("AAPL", 190.0)]]
        assert latest_eod_closes(client) == {"AAPL": 190.0}
        assert client.get_grouped_daily_aggs.call_count == 3

    def test_starts_from_new_york_yesterday(self):
        """Local clock already on Oct 18 (UTC+8) while New York is still Oct 17."""
        client = MagicMock()
        client.get_grouped_daily_aggs.return_value = [_bar("AAPL", 190.0)]
        ny_now = datetime(2026, 10, 17, 13, 19, tzinfo=MARKET_TZ)
        with patch("app.market.massive_client.datetime") as dt:
            dt.now.return_value = ny_now
            latest_eod_closes(client)

        dt.now.assert_called_once_with(MARKET_TZ)
        assert client.get_grouped_daily_aggs.call_args.args[0] == "2026-10-16"

    def test_gives_up_after_max_days(self):
        client = MagicMock()
        client.get_grouped_daily_aggs.return_value = []
        assert latest_eod_closes(client, max_days_back=2) == {}
        assert client.get_grouped_daily_aggs.call_count == 2


@pytest.mark.asyncio
class TestMassiveDataSource:
    """MassiveDataSource behaviour with a mocked RESTClient."""

    async def test_poll_updates_cache(self):
        source, cache = _source(["AAPL", "GOOGL"])
        source._client.get_snapshot_all.return_value = [
            _developer_snap("AAPL", 190.50),
            _developer_snap("GOOGL", 175.25),
        ]
        await source._poll_once()

        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("GOOGL") == 175.25

    async def test_timestamp_converted_from_nanoseconds(self):
        source, cache = _source(["AAPL"])
        source._client.get_snapshot_all.return_value = [_developer_snap("AAPL", 190.50)]
        await source._poll_once()

        assert cache.get("AAPL").timestamp == 1760790000.0

    async def test_snapshot_without_price_skipped(self):
        source, cache = _source(["AAPL", "BAD"])
        source._client.get_snapshot_all.return_value = [
            _developer_snap("AAPL", 190.50),
            TickerSnapshot.from_dict({"ticker": "BAD"}),
        ]
        await source._poll_once()

        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("BAD") is None

    async def test_api_error_does_not_crash(self):
        source, cache = _source(["AAPL"])
        source._client.get_snapshot_all.side_effect = Exception("network error")
        await source._poll_once()  # Should not raise

        assert cache.get_price("AAPL") is None

    async def test_other_bad_response_stays_in_snapshot_mode(self):
        source, cache = _source(["AAPL"])
        source._client.get_snapshot_all.side_effect = BadResponse('{"status":"ERROR"}')
        await source._poll_once()

        assert source._mode == "snapshot"
        assert cache.get_price("AAPL") is None

    async def test_not_authorized_falls_back_to_eod(self):
        source, cache = _source(["AAPL", "MSFT"])
        source._client.get_snapshot_all.side_effect = BadResponse(NOT_AUTHORIZED)
        source._client.get_grouped_daily_aggs.return_value = [
            _bar("AAPL", 190.0),
            _bar("MSFT", 420.0),
            _bar("TSLA", 250.0),
        ]
        await source._poll_once()

        assert source._mode == "eod"
        assert source._interval == 900.0
        assert cache.get_price("AAPL") == 190.0
        assert cache.get_price("MSFT") == 420.0
        assert cache.get_price("TSLA") is None  # Not watched

    async def test_eod_add_ticker_priced_without_api_call(self):
        source, cache = _source(["AAPL"])
        source._client.get_snapshot_all.side_effect = BadResponse(NOT_AUTHORIZED)
        source._client.get_grouped_daily_aggs.return_value = [_bar("AAPL", 190.0), _bar("TSLA", 250.0)]
        await source._poll_once()
        calls = source._client.get_grouped_daily_aggs.call_count

        await source.add_ticker("TSLA")

        assert cache.get_price("TSLA") == 250.0
        assert source._client.get_grouped_daily_aggs.call_count == calls

    async def test_snapshot_request_url(self):
        """Real SDK builds the URL; only the HTTP layer is stubbed."""
        source, cache = _source(["AAPL"])
        source._client = RESTClient(api_key="test-key")
        body = b'{"status":"OK","tickers":[{"ticker":"AAPL","lastTrade":{"p":190.5,"t":1760790000000000000}}]}'
        source._client.client.request = MagicMock(return_value=MagicMock(status=200, data=body))
        await source._poll_once()

        url = source._client.client.request.call_args.args[1]
        assert url == "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers"
        assert cache.get_price("AAPL") == 190.5

    async def test_add_ticker(self):
        source, _ = _source()
        await source.add_ticker("AAPL")
        assert "AAPL" in source.get_tickers()

    async def test_add_ticker_normalizes(self):
        source, _ = _source()
        await source.add_ticker("  aapl  ")
        assert source.get_tickers() == ["AAPL"]

    async def test_remove_ticker(self):
        source, cache = _source(["AAPL", "GOOGL"])
        cache.update("AAPL", 190.00)

        await source.remove_ticker("AAPL")
        assert "AAPL" not in source.get_tickers()
        assert cache.get("AAPL") is None

    async def test_get_tickers(self):
        source, _ = _source(["AAPL", "GOOGL"])
        assert source.get_tickers() == ["AAPL", "GOOGL"]

    async def test_empty_tickers_skips_poll(self):
        source, _ = _source([])
        await source._poll_once()
        source._client.get_snapshot_all.assert_not_called()

    async def test_stop_is_idempotent(self):
        source, _ = _source()
        await source.stop()
        await source.stop()  # Should not raise

    async def test_start_polls_immediately_then_stop_cancels(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)

        with patch("app.market.massive_client.RESTClient") as client_cls:
            client_cls.return_value.get_snapshot_all.return_value = [_developer_snap("AAPL", 190.50)]
            await source.start(["aapl"])

        assert cache.get_price("AAPL") == 190.50
        assert source._task is not None and not source._task.done()

        await source.stop()
        assert source._task is None
