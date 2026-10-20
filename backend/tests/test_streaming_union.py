import asyncio

import pytest

from app import db, main, streaming
from app.market.seed_prices import DEFAULT_TICKERS


def test_streamed_tickers_order(seed_position):
    seed_position("ZZZZ", 1, 50)
    seed_position("AAPL", 1, 50)
    assert streaming.streamed_tickers() == DEFAULT_TICKERS + ["ZZZZ"]


def test_is_watched_or_held(seed_position):
    db.init_db()
    assert streaming.is_watched_or_held("AAPL")
    assert not streaming.is_watched_or_held("ZZZZ")
    seed_position("ZZZZ", 1, 50)
    assert streaming.is_watched_or_held("ZZZZ")


async def test_startup_streams_held(seed_position):
    seed_position("ZZZZ", 1, 50)
    async with main.app.router.lifespan_context(main.app):
        assert "ZZZZ" in main.source.get_tickers()
        assert main.cache.get("ZZZZ") is not None


def streaming_now(ticker):
    return ticker in main.source.get_tickers() and main.cache.get(ticker) is not None


async def buy(client, ticker, qty=1):
    return await client.post(
        "/api/portfolio/trade", json={"ticker": ticker, "side": "buy", "quantity": qty}
    )


async def sell(client, ticker, qty=1):
    return await client.post(
        "/api/portfolio/trade", json={"ticker": ticker, "side": "sell", "quantity": qty}
    )


async def test_unwatch_held_keeps_streaming(client):
    assert (await buy(client, "AAPL")).status_code == 200
    assert (await client.delete("/api/watchlist/AAPL")).status_code == 204
    assert streaming_now("AAPL")


async def test_unwatch_not_held_stops(client):
    assert (await client.delete("/api/watchlist/NFLX")).status_code == 204
    assert "NFLX" not in main.source.get_tickers()
    assert main.cache.get("NFLX") is None


async def test_sell_out_unwatched_stops(client):
    assert (await buy(client, "ZZZZ")).status_code == 200
    assert streaming_now("ZZZZ")
    r = await sell(client, "ZZZZ")
    assert r.status_code == 200
    assert r.json()["position"] is None
    assert "ZZZZ" not in main.source.get_tickers()
    assert main.cache.get("ZZZZ") is None


async def test_sell_out_watched_keeps(client):
    assert (await buy(client, "AAPL")).status_code == 200
    assert (await sell(client, "AAPL")).status_code == 200
    assert streaming_now("AAPL")


async def test_failed_unwatched_trade_stops(client):
    assert (await buy(client, "QQQQ", 1000000)).status_code == 400
    assert "QQQQ" not in main.source.get_tickers()
    assert main.cache.get("QQQQ") is None


async def test_concurrent_trades_keep_fill_price(client):
    """A failing trade racing a buy on a new ticker must not re-seed the held ticker's price."""
    for ticker in ("QAXX", "QBXX", "QCXX", "QDXX", "QEXX"):
        fail, ok = await asyncio.gather(buy(client, ticker, 1000000), buy(client, ticker))
        assert fail.status_code == 400 and ok.status_code == 200
        assert streaming_now(ticker)
        assert main.cache.get(ticker).price == pytest.approx(ok.json()["trade"]["price"], rel=0.1)
