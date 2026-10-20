"""Portfolio value snapshots: recording, bounded history, periodic loop."""

import asyncio
import logging
from contextlib import closing
from datetime import UTC, datetime
from uuid import uuid4

from app import portfolio
from app.db import connect, db_path
from app.market.cache import PriceCache

logger = logging.getLogger(__name__)


def record_snapshot(cache: PriceCache) -> dict:
    """Insert the current total portfolio value and return the stored row."""
    total = portfolio.portfolio_view(cache)["total_value"]
    now = datetime.now(UTC).isoformat()
    with closing(connect(db_path())) as conn, conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, 'default', ?, ?)",
            (str(uuid4()), total, now),
        )
    return {"total_value": total, "recorded_at": now}


def history(limit: int = 500) -> list[dict]:
    """Return the most recent snapshots, oldest first."""
    with closing(connect(db_path())) as conn:
        rows = conn.execute(
            "SELECT total_value, recorded_at FROM ("
            "SELECT rowid AS r, total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = 'default' ORDER BY rowid DESC LIMIT ?) ORDER BY r",
            (limit,),
        ).fetchall()
    return [{"total_value": r["total_value"], "recorded_at": r["recorded_at"]} for r in rows]


async def snapshot_loop(cache: PriceCache, interval: float = 30.0) -> None:
    """Record a snapshot every `interval` seconds until cancelled."""
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(record_snapshot, cache)
        except Exception:
            logger.exception("snapshot failed")
