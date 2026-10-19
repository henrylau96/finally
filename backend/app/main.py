"""FastAPI application: API routes, simulator lifespan, static frontend."""

import asyncio
import os
import signal
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.api.health import router as health_router
from app.api.stream import create_stream_router, shutdown
from app.api.watchlist import create_watchlist_router
from app.market import PriceCache, create_market_data_source

STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).parent.parent / "static"))

cache = PriceCache()
source = create_market_data_source(cache)


def end_streams_on_exit_signal() -> None:
    """Chain SIGINT/SIGTERM so SSE streams end before uvicorn waits for connections to close."""
    for sig in (signal.SIGINT, signal.SIGTERM):
        previous = signal.getsignal(sig)

        def handler(signum, frame, previous=previous):
            shutdown.set()
            previous(signum, frame)

        signal.signal(sig, handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    end_streams_on_exit_signal()
    await asyncio.to_thread(db.init_db)
    tickers = await asyncio.to_thread(db.list_tickers)
    await source.start(tickers)
    yield
    await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(health_router)
app.include_router(create_stream_router(cache))
app.include_router(create_watchlist_router(cache, source))
STATIC_DIR.mkdir(parents=True, exist_ok=True)  # StaticFiles raises per request if missing
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True, check_dir=False), name="static")
