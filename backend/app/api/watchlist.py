"""Watchlist REST endpoints backed by SQLite and the market data source."""

import asyncio
import re

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, field_validator

from app import db
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource


class AddTicker(BaseModel):
    ticker: str

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize(cls, v):
        """Trim, uppercase and require 1-5 letters."""
        v = str(v).strip().upper()
        if not re.fullmatch(r"[A-Z]{1,5}", v):
            raise ValueError("ticker must be 1-5 letters")
        return v


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
    async def add(body: AddTicker, response: Response) -> dict:
        row, created = await asyncio.to_thread(db.add_ticker, body.ticker)
        if created:
            await source.add_ticker(body.ticker)
        else:
            response.status_code = 200
        return item(row)

    @router.delete("/api/watchlist/{ticker}", status_code=204)
    async def remove(ticker: str) -> None:
        t = ticker.strip().upper()
        if not await asyncio.to_thread(db.remove_ticker, t):
            raise HTTPException(404, "Ticker not on watchlist")
        await source.remove_ticker(t)

    return router
