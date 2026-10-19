import asyncio

import pytest

from app import main


async def trade(client, **body):
    return await client.post("/api/portfolio/trade", json=body)


async def test_get_portfolio_fresh(client):
    r = await client.get("/api/portfolio")
    assert r.status_code == 200
    assert r.json() == {"cash_balance": 10000.0, "total_value": 10000.0,
                        "unrealized_pnl": 0.0, "positions": []}


async def test_buy(client):
    r = await trade(client, ticker=" aapl ", side="buy", quantity=2)
    assert r.status_code == 200
    body = r.json()
    assert body["trade"]["ticker"] == "AAPL"
    assert body["cash_balance"] == round(10000 - round(2 * body["trade"]["price"], 2), 2)
    assert body["position"]["quantity"] == 2
    got = (await client.get("/api/portfolio")).json()
    assert [p["ticker"] for p in got["positions"]] == ["AAPL"]


async def test_sell_partial_and_all(client):
    buy = (await trade(client, ticker="AAPL", side="buy", quantity=3)).json()
    r = (await trade(client, ticker="AAPL", side="sell", quantity=1)).json()
    assert r["position"]["quantity"] == 2
    assert r["position"]["avg_cost"] == buy["trade"]["price"]
    r = (await trade(client, ticker="AAPL", side="sell", quantity=2)).json()
    assert r["position"] is None
    assert (await client.get("/api/portfolio")).json()["positions"] == []


async def test_insufficient_cash_api(client):
    r = await trade(client, ticker="AAPL", side="buy", quantity=1000000)
    assert r.status_code == 400 and r.json()["detail"].startswith("Insufficient cash")
    assert (await client.get("/api/portfolio")).json()["cash_balance"] == 10000.0


async def test_oversell_api(client):
    r = await trade(client, ticker="AAPL", side="sell", quantity=5)
    assert r.status_code == 400
    assert r.json()["detail"] == "Cannot sell 5 AAPL; you hold 0"


@pytest.mark.parametrize("body", [
    {"ticker": 123, "side": "buy", "quantity": 1},
    {"ticker": True, "side": "buy", "quantity": 1},
    {"ticker": "A1", "side": "buy", "quantity": 1},
    {"ticker": "TOOLONG", "side": "buy", "quantity": 1},
    {"ticker": "AAPL", "side": "BUY", "quantity": 1},
    {"ticker": "AAPL", "side": "hold", "quantity": 1},
    {"ticker": "AAPL", "side": "buy", "quantity": 0},
    {"ticker": "AAPL", "side": "buy", "quantity": -1},
    {"ticker": "AAPL", "side": "buy", "quantity": True},
    {"ticker": "AAPL", "side": "buy", "quantity": "5"},
    {"ticker": "AAPL", "side": "buy", "quantity": 1.00001},
    {"ticker": "AAPL", "side": "buy", "quantity": 1000001},
    {"side": "buy", "quantity": 1},
    {"ticker": "AAPL", "quantity": 1},
    {"ticker": "AAPL", "side": "buy"},
])
async def test_invalid_trade(client, body):
    assert (await trade(client, **body)).status_code == 422
    assert (await client.get("/api/portfolio")).json()["positions"] == []


async def test_nan_quantity(client):
    r = await client.post("/api/portfolio/trade", headers={"content-type": "application/json"},
                          content='{"ticker":"AAPL","side":"buy","quantity":NaN}')
    assert r.status_code == 422


async def test_fractional_noise_accepted(client):
    await trade(client, ticker="AAPL", side="buy", quantity=2.3)
    r = await trade(client, ticker="AAPL", side="sell", quantity=1.2999999999999998)
    assert r.status_code == 200 and r.json()["position"]["quantity"] == 1.0


async def test_concurrent_buys(client):
    p = main.cache.get("AAPL").price
    q = round(6000 / p, 4)
    rs = await asyncio.gather(*[trade(client, ticker="AAPL", side="buy", quantity=q) for _ in range(2)])
    assert sorted(r.status_code for r in rs) == [200, 400]


async def test_unknown_ticker_trade(client):
    r = await trade(client, ticker="ZZZZ", side="buy", quantity=1)
    assert r.status_code == 200 and r.json()["trade"]["price"] > 0
