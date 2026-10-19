"""Background task that records portfolio value periodically."""

from __future__ import annotations

import asyncio
import logging

from app import db
from app.market import PriceCache

from .trading import total_value

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL = 30.0


async def snapshot_loop(
    price_cache: PriceCache, interval: float = SNAPSHOT_INTERVAL, user_id: str = "default"
) -> None:
    """Record a portfolio snapshot every `interval` seconds until cancelled."""
    while True:
        await asyncio.sleep(interval)
        try:
            db.record_snapshot(total_value(price_cache, user_id), user_id)
        except Exception:
            logger.exception("Portfolio snapshot failed")
