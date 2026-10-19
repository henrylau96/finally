"""Tests for MassiveDataSource (mocked)."""

from unittest.mock import MagicMock, patch

import pytest
from massive.exceptions import BadResponse

from app.market.cache import PriceCache
from app.market.massive_client import MassiveDataSource


def _make_snapshot(ticker: str, price: float, timestamp_ms: int) -> MagicMock:
    """Create a mock Massive snapshot object."""
    snap = MagicMock()
    snap.ticker = ticker
    snap.last_trade = MagicMock()
    snap.last_trade.price = price
    snap.last_trade.timestamp = timestamp_ms
    return snap


@pytest.mark.asyncio
class TestMassiveDataSource:
    """Unit tests for MassiveDataSource with mocked API."""

    async def test_poll_updates_cache(self):
        """Test that polling updates the cache."""
        cache = PriceCache()
        source = MassiveDataSource(
            api_key="test-key",
            price_cache=cache,
            poll_interval=60.0,  # Long interval so the loop doesn't auto-poll
        )
        source._tickers = ["AAPL", "GOOGL"]
        source._client = MagicMock()  # Satisfy the _poll_once guard

        mock_snapshots = [
            _make_snapshot("AAPL", 190.50, 1707580800000),
            _make_snapshot("GOOGL", 175.25, 1707580800000),
        ]

        with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
            await source._poll_once()

        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("GOOGL") == 175.25

    async def test_malformed_snapshot_skipped(self):
        """Test that malformed snapshots are skipped gracefully."""
        cache = PriceCache()
        source = MassiveDataSource(
            api_key="test-key",
            price_cache=cache,
            poll_interval=60.0,
        )
        source._tickers = ["AAPL", "BAD"]
        source._client = MagicMock()  # Satisfy the _poll_once guard

        good_snap = _make_snapshot("AAPL", 190.50, 1707580800000)
        bad_snap = MagicMock()
        bad_snap.ticker = "BAD"
        bad_snap.last_trade = None  # Will cause AttributeError

        with patch.object(source, "_fetch_snapshots", return_value=[good_snap, bad_snap]):
            await source._poll_once()

        # Good ticker processed, bad one skipped
        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("BAD") is None

    async def test_api_error_does_not_crash(self):
        """Test that API errors don't crash the poller."""
        cache = PriceCache()
        source = MassiveDataSource(
            api_key="test-key",
            price_cache=cache,
            poll_interval=60.0,
        )
        source._tickers = ["AAPL"]
        source._client = MagicMock()  # Satisfy the _poll_once guard

        with patch.object(source, "_fetch_snapshots", side_effect=Exception("network error")):
            await source._poll_once()  # Should not raise

        assert cache.get_price("AAPL") is None  # No update happened

    async def test_timestamp_conversion(self):
        """Test that timestamps are converted from milliseconds to seconds."""
        cache = PriceCache()
        source = MassiveDataSource(
            api_key="test-key",
            price_cache=cache,
            poll_interval=60.0,
        )
        source._tickers = ["AAPL"]
        source._client = MagicMock()  # Satisfy the _poll_once guard

        mock_snapshots = [_make_snapshot("AAPL", 190.50, 1707580800000)]

        with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
            await source._poll_once()

        update = cache.get("AAPL")
        assert update is not None
        assert update.timestamp == 1707580800.0  # Converted to seconds

    async def test_add_ticker(self):
        """Test adding a ticker."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache)

        await source.add_ticker("AAPL")
        assert "AAPL" in source.get_tickers()

    async def test_add_ticker_uppercase_normalization(self):
        """Test that tickers are normalized to uppercase."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache)

        await source.add_ticker("aapl")
        assert "AAPL" in source.get_tickers()

    async def test_add_ticker_strips_whitespace(self):
        """Test that ticker whitespace is stripped."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache)

        await source.add_ticker("  AAPL  ")
        assert "AAPL" in source.get_tickers()

    async def test_remove_ticker(self):
        """Test removing a ticker."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache)
        source._tickers = ["AAPL", "GOOGL"]
        cache.update("AAPL", 190.00)

        await source.remove_ticker("AAPL")
        assert "AAPL" not in source.get_tickers()
        assert cache.get("AAPL") is None

    async def test_get_tickers(self):
        """Test getting the list of active tickers."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache)
        source._tickers = ["AAPL", "GOOGL"]

        tickers = source.get_tickers()
        assert tickers == ["AAPL", "GOOGL"]

    async def test_empty_tickers_skips_poll(self):
        """Test that polling is skipped when there are no tickers."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache)
        source._tickers = []

        # Should not call _fetch_snapshots
        with patch.object(source, "_fetch_snapshots") as mock_fetch:
            await source._poll_once()
            mock_fetch.assert_not_called()

    async def test_stop_is_idempotent(self):
        """Test that stop() can be called multiple times."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache)

        await source.stop()
        await source.stop()  # Should not raise

    async def test_stop_cancels_task(self):
        """Test that stop() cancels the polling task."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=10.0)

        # Mock the client and start
        with patch("app.market.massive_client.RESTClient"):
            with patch.object(source, "_fetch_snapshots", return_value=[]):
                await source.start(["AAPL"])

        # Verify task is running
        assert source._task is not None
        assert not source._task.done()

        # Stop and verify task is cancelled
        await source.stop()
        assert source._task is None

    async def test_start_immediate_poll(self):
        """Test that start() does an immediate poll before starting the loop."""
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)

        mock_snapshots = [_make_snapshot("AAPL", 190.50, 1707580800000)]

        with patch("app.market.massive_client.RESTClient"):
            with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
                await source.start(["AAPL"])

        # Cache should have data immediately from the first poll
        assert cache.get_price("AAPL") == 190.50

        await source.stop()


def _make_agg(ticker: str, close: float, timestamp_ms: int) -> MagicMock:
    """Create a mock grouped daily aggregate."""
    agg = MagicMock()
    agg.ticker, agg.close, agg.timestamp = ticker, close, timestamp_ms
    return agg


def _source_with_client(tickers: list[str]) -> tuple[MassiveDataSource, PriceCache]:
    cache = PriceCache()
    source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
    source._tickers = tickers
    source._client = MagicMock()
    return source, cache


@pytest.mark.asyncio
class TestMassiveFreeTierFallback:
    """Snapshot URL fix and end-of-day fallback for plans without snapshot access."""

    async def test_snapshot_uses_string_market_type(self):
        source, _ = _source_with_client(["AAPL"])
        source._client.get_snapshot_all.return_value = []
        await source._poll_once()
        source._client.get_snapshot_all.assert_called_once_with(
            market_type="stocks", tickers=["AAPL"]
        )

    async def test_not_authorized_falls_back_to_eod_closes(self):
        source, cache = _source_with_client(["AAPL", "MSFT"])
        source._client.get_snapshot_all.side_effect = BadResponse('{"status":"NOT_AUTHORIZED"}')
        source._client.get_grouped_daily_aggs.return_value = [
            _make_agg("AAPL", 343.46, 1792180800000),
            _make_agg("MSFT", 529.05, 1792180800000),
            _make_agg("ZZZZ", 1.0, 1792180800000),
        ]
        await source._poll_once()
        assert cache.get_price("AAPL") == 343.46
        assert cache.get_price("MSFT") == 529.05
        assert cache.get_price("ZZZZ") is None
        assert source._eod_date is not None

        await source._poll_once()
        assert source._client.get_snapshot_all.call_count == 1  # Sticky fallback

    async def test_eod_walks_back_past_empty_days(self):
        source, cache = _source_with_client(["AAPL"])
        source._client.get_snapshot_all.side_effect = BadResponse('{"status":"NOT_AUTHORIZED"}')
        source._client.get_grouped_daily_aggs.side_effect = [
            [],
            [_make_agg("AAPL", 340.0, 1792180800000)],
        ]
        await source._poll_once()
        assert cache.get_price("AAPL") == 340.0
        assert source._client.get_grouped_daily_aggs.call_count == 2

    async def test_eod_walk_back_is_capped(self):
        source, cache = _source_with_client(["AAPL"])
        source._client.get_snapshot_all.side_effect = BadResponse('{"status":"NOT_AUTHORIZED"}')
        source._client.get_grouped_daily_aggs.return_value = []
        await source._poll_once()  # Logs the error, does not raise
        assert cache.get_price("AAPL") is None
        assert source._client.get_grouped_daily_aggs.call_count <= 7

    async def test_other_errors_do_not_fall_back(self):
        source, _ = _source_with_client(["AAPL"])
        source._client.get_snapshot_all.side_effect = BadResponse("404 page not found")
        await source._poll_once()
        source._client.get_grouped_daily_aggs.assert_not_called()
        assert source._eod_date is None
