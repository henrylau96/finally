"""FastAPI application: API routes, simulator lifespan, static frontend."""

import asyncio
import os
import signal
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app import db, snapshots, streaming
from app.api.health import router as health_router
from app.api.portfolio import create_portfolio_router
from app.api.stream import create_stream_router, shutdown
from app.api.watchlist import create_watchlist_router
from app.chat.router import create_chat_router
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
    app.state.trade_lock = asyncio.Lock()
    tickers = await asyncio.to_thread(streaming.streamed_tickers)
    await source.start(tickers)
    await asyncio.to_thread(snapshots.record_snapshot, cache)
    app.state.snapshot_task = asyncio.create_task(snapshots.snapshot_loop(cache), name="snapshot-loop")
    yield
    app.state.snapshot_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.snapshot_task
    await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return 422 without echoing input; a NaN input is not serializable as JSON."""
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=422)


app.include_router(health_router)
app.include_router(create_stream_router(cache))
app.include_router(create_watchlist_router(cache, source))
app.include_router(create_portfolio_router(cache, source))
app.include_router(create_chat_router(cache, source))
STATIC_DIR.mkdir(parents=True, exist_ok=True)  # StaticFiles raises per request if missing
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True, check_dir=False), name="static")
