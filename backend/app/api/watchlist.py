"""Watchlist REST endpoints backed by SQLite and the market data source."""

import asyncio

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app import db, services
from app.api.schemas import Ticker
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource


class AddTicker(BaseModel):
    ticker: Ticker


def create_watchlist_router(cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter()

    def item(row: dict) -> dict:
        """Merge a watchlist row with its latest cached price."""
        u = cache.get(row["ticker"])
        prices = {"price": None, "previous_price": None, "direction": None, "day_change_pct": None}
        if u is not None:
            prices = {
                "price": u.price,
                "previous_price": u.previous_price,
                "direction": u.direction,
                "day_change_pct": u.day_change_pct,
            }
        return {"ticker": row["ticker"], **prices, "added_at": row["added_at"]}

    @router.get("/api/watchlist")
    async def list_watchlist() -> list[dict]:
        rows = await asyncio.to_thread(db.list_watchlist)
        return [item(r) for r in rows]

    @router.post("/api/watchlist", status_code=201)
    async def add(body: AddTicker, request: Request, response: Response) -> dict:
        row, created = await services.add_to_watchlist(request.app, source, body.ticker)
        if not created:
            response.status_code = 200
        return item(row)

    @router.delete("/api/watchlist/{ticker}", status_code=204)
    async def remove(ticker: str, request: Request) -> None:
        t = ticker.strip().upper()
        try:
            await services.remove_from_watchlist(request.app, source, t)
        except services.WatchlistError as e:
            raise HTTPException(404, str(e)) from e

    return router
