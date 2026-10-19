"""Watchlist service: keeps the DB watchlist and the market data source in sync."""

from __future__ import annotations

import re

from app import db
from app.market import MarketDataSource, PriceCache

TICKER_PATTERN = re.compile(r"^[A-Z.]{1,10}$")


def normalize_ticker(ticker: str) -> str:
    """Uppercase and validate a ticker symbol. Raises ValueError if invalid."""
    ticker = ticker.upper().strip()
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(f"Invalid ticker '{ticker}'")
    return ticker


def get_watchlist_with_prices(price_cache: PriceCache, user_id: str = "default") -> list[dict]:
    """Return watchlist tickers in order, with latest price fields (None if no price yet)."""
    rows = []
    for ticker in db.get_watchlist(user_id):
        update = price_cache.get(ticker)
        rows.append(
            {
                "ticker": ticker,
                "price": update.price if update else None,
                "previous_price": update.previous_price if update else None,
                "change": update.change if update else None,
                "change_percent": update.change_percent if update else None,
                "direction": update.direction if update else None,
            }
        )
    return rows


async def add_watchlist_ticker(
    ticker: str, source: MarketDataSource, user_id: str = "default"
) -> bool:
    """Add a ticker and start streaming it. Returns False if already watched."""
    ticker = normalize_ticker(ticker)
    if not db.add_to_watchlist(ticker, user_id):
        return False
    await source.add_ticker(ticker)
    return True


async def remove_watchlist_ticker(
    ticker: str, source: MarketDataSource, user_id: str = "default"
) -> bool:
    """Remove a ticker; stop streaming it unless still held. Returns False if absent."""
    ticker = ticker.upper().strip()
    if not db.remove_from_watchlist(ticker, user_id):
        return False
    if db.get_position(ticker, user_id) is None:
        await source.remove_ticker(ticker)
    return True


def tracked_tickers(user_id: str = "default") -> list[str]:
    """Return watchlist tickers plus any held tickers not on the watchlist."""
    tickers = db.get_watchlist(user_id)
    held = [p["ticker"] for p in db.get_positions(user_id) if p["ticker"] not in tickers]
    return tickers + held
