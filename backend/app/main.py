"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.api import create_portfolio_router, create_watchlist_router, health_router
from app.llm import create_chat_router
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.portfolio import snapshot_loop, tracked_tickers

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR.parent / ".env")

price_cache = PriceCache()
market_source = create_market_data_source(price_cache)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the DB, start market data and snapshots; stop them on shutdown."""
    db.init_db()
    await market_source.start(tracked_tickers())
    snapshot_task = asyncio.create_task(snapshot_loop(price_cache))
    yield
    snapshot_task.cancel()
    await market_source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(health_router)
app.include_router(create_stream_router(price_cache))
app.include_router(create_portfolio_router(price_cache))
app.include_router(create_watchlist_router(price_cache, market_source))
app.include_router(create_chat_router(price_cache, market_source))

static_dir = Path(os.environ.get("STATIC_DIR", BACKEND_DIR / "static"))
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
