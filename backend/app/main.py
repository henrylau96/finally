"""FastAPI application: API routes, simulator lifespan, static frontend."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.stream import create_stream_router
from app.market import DEFAULT_TICKERS, PriceCache, create_market_data_source

STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).parent.parent / "static"))

cache = PriceCache()
source = create_market_data_source(cache)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await source.start(DEFAULT_TICKERS)
    yield
    await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(health_router)
app.include_router(create_stream_router(cache))
STATIC_DIR.mkdir(parents=True, exist_ok=True)  # StaticFiles raises per request if missing
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True, check_dir=False), name="static")
