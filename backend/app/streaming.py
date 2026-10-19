"""The streamed ticker set: watchlist plus held positions."""

import asyncio
from contextlib import closing

from app import db
from app.market.interface import MarketDataSource


def streamed_tickers() -> list[str]:
    """Watchlist tickers in order, then held tickers not already present."""
    with closing(db.connect(db.db_path())) as conn:
        watched = [r[0] for r in conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = 'default' ORDER BY rowid")]
        held = [r[0] for r in conn.execute(
            "SELECT ticker FROM positions WHERE user_id = 'default' ORDER BY rowid")]
    return watched + [t for t in held if t not in watched]


def is_watched_or_held(ticker: str) -> bool:
    """True if the ticker is on the watchlist or has a position."""
    with closing(db.connect(db.db_path())) as conn:
        return any(
            conn.execute(
                f"SELECT EXISTS(SELECT 1 FROM {table} WHERE user_id = 'default' AND ticker = ?)",
                (ticker,),
            ).fetchone()[0]
            for table in ("watchlist", "positions")
        )


async def reconcile_stream(source: MarketDataSource, ticker: str) -> None:
    """Stream the ticker if watched or held, otherwise stop streaming it."""
    if await asyncio.to_thread(is_watched_or_held, ticker):
        await source.add_ticker(ticker)
    else:
        await source.remove_ticker(ticker)
