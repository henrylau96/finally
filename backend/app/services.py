"""Lock-owning trade and watchlist operations shared by REST routes and chat.

These functions acquire app.state.trade_lock themselves; callers must not hold it.
"""

import asyncio
import logging

from fastapi import FastAPI

from app import db, portfolio, snapshots
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.streaming import reconcile_stream

logger = logging.getLogger(__name__)


class WatchlistError(Exception):
    """Raised when a watchlist change is not possible."""


async def place_trade(
    app: FastAPI, cache: PriceCache, source: MarketDataSource, ticker: str, side: str, quantity: float
) -> dict:
    """Execute a market order at the cached price; raises portfolio.TradeError on failure."""
    async with app.state.trade_lock:
        try:
            if cache.get(ticker) is None:
                await source.add_ticker(ticker)
            update = cache.get(ticker)
            if update is None:
                raise portfolio.TradeError(f"No price available for {ticker}")
            result = await asyncio.to_thread(portfolio.execute_trade, ticker, side, quantity, update.price)
        finally:
            await reconcile_stream(source, ticker)
    try:
        await asyncio.to_thread(snapshots.record_snapshot, cache)
    except Exception:
        logger.exception("post-trade snapshot failed")
    return result


async def add_to_watchlist(app: FastAPI, source: MarketDataSource, ticker: str) -> tuple[dict, bool]:
    """Add a ticker; returns (row, created)."""
    async with app.state.trade_lock:
        row, created = await asyncio.to_thread(db.add_ticker, ticker)
        if created:
            await source.add_ticker(ticker)
    return row, created


async def remove_from_watchlist(app: FastAPI, source: MarketDataSource, ticker: str) -> None:
    """Remove a ticker; raises WatchlistError if it is not watched."""
    async with app.state.trade_lock:
        if not await asyncio.to_thread(db.remove_ticker, ticker):
            raise WatchlistError("Ticker not on watchlist")
        await reconcile_stream(source, ticker)
