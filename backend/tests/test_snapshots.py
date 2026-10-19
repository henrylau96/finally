import asyncio
from contextlib import closing
from uuid import uuid4

from app import db, main, snapshots
from app.market import PriceCache


async def hist(client):
    return (await client.get("/api/portfolio/history")).json()


async def test_startup_snapshot(client):
    h = await hist(client)
    assert len(h) >= 1
    assert set(h[0]) == {"total_value", "recorded_at"}
    assert h[0]["total_value"] == 10000.0


async def test_snapshot_after_trade(client):
    before = len(await hist(client))
    r = await client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 1})
    assert r.status_code == 200
    h = await hist(client)
    assert len(h) == before + 1
    total = (await client.get("/api/portfolio")).json()["total_value"]
    assert abs(h[-1]["total_value"] - total) < 1.0


async def test_no_snapshot_after_failed_trade(client):
    before = len(await hist(client))
    r = await client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "sell", "quantity": 5})
    assert r.status_code == 400
    assert len(await hist(client)) == before


def test_history_bounded(db_env):
    db.init_db()
    with closing(db.connect(db.db_path())) as conn, conn:
        for i in range(600):
            conn.execute(
                "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
                "VALUES (?, 'default', ?, ?)",
                (str(uuid4()), float(i), "2026-01-01T00:00:00+00:00"),
            )
    h = snapshots.history()
    assert len(h) == 500
    assert h[0]["total_value"] == 100
    assert h[-1]["total_value"] == 599


async def test_snapshot_loop(db_env):
    db.init_db()
    task = asyncio.create_task(snapshots.snapshot_loop(PriceCache(), interval=0.05))
    await asyncio.sleep(0.3)
    task.cancel()
    assert len(snapshots.history()) >= 3


async def test_task_cancelled_on_shutdown(db_env):
    async with main.app.router.lifespan_context(main.app):
        pass
    assert main.app.state.snapshot_task.done()
