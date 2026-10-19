import pytest

from app.main import app, cache, source
from app.market import DEFAULT_TICKERS

KEYS = {"ticker", "price", "previous_price", "direction", "day_change_pct", "added_at"}


async def tickers(client):
    return [r["ticker"] for r in (await client.get("/api/watchlist")).json()]


async def test_list(client):
    """GET returns the ten seeded tickers in order with the contracted keys."""
    response = await client.get("/api/watchlist")
    assert response.status_code == 200
    rows = response.json()
    assert [r["ticker"] for r in rows] == list(DEFAULT_TICKERS)
    for row in rows:
        assert set(row) == KEYS
        assert row["price"] > 0


async def test_add(client):
    """POST normalizes the ticker, returns 201 and starts streaming it."""
    response = await client.post("/api/watchlist", json={"ticker": " pypl "})
    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "PYPL"
    assert isinstance(body["price"], float)
    assert "PYPL" in await tickers(client)
    assert "PYPL" in source.get_tickers()
    assert cache.get("PYPL") is not None


@pytest.mark.parametrize("bad", ["TOOLONG", "A1", "", "BRK.B"])
async def test_invalid(client, bad):
    """Invalid tickers are rejected with 422 and leave the list unchanged."""
    response = await client.post("/api/watchlist", json={"ticker": bad})
    assert response.status_code == 422
    assert len(await tickers(client)) == 10


async def test_duplicate(client):
    """Adding an existing ticker returns 200 and does not add a second row."""
    response = await client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert response.status_code == 200
    assert response.json()["ticker"] == "AAPL"
    assert (await tickers(client)).count("AAPL") == 1


async def test_remove(client):
    """DELETE returns 204, stops streaming, and a second DELETE is 404."""
    response = await client.delete("/api/watchlist/nflx")
    assert response.status_code == 204
    assert response.content == b""
    assert "NFLX" not in await tickers(client)
    assert "NFLX" not in source.get_tickers()
    assert "NFLX" not in cache.get_all()
    assert (await client.delete("/api/watchlist/nflx")).status_code == 404


async def reenter(db_env):
    """Open a fresh lifespan and client on the existing DB."""
    import httpx

    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_persist_across_restart(db_env):
    """Add and remove survive a lifespan restart."""
    async with app.router.lifespan_context(app):
        async with await reenter(db_env) as c:
            await c.delete("/api/watchlist/NFLX")
            await c.post("/api/watchlist", json={"ticker": "PYPL"})
    async with app.router.lifespan_context(app):
        async with await reenter(db_env) as c:
            names = await tickers(c)
    assert "PYPL" in names
    assert "NFLX" not in names


async def test_empty_watchlist(db_env):
    """An emptied watchlist stays empty after restart."""
    async with app.router.lifespan_context(app):
        async with await reenter(db_env) as c:
            for t in DEFAULT_TICKERS:
                await c.delete(f"/api/watchlist/{t}")
            assert (await c.get("/api/watchlist")).json() == []
    async with app.router.lifespan_context(app):
        async with await reenter(db_env) as c:
            assert (await c.get("/api/watchlist")).json() == []
