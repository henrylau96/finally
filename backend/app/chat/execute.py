"""Execute LLM-requested actions through the same services and validation as the REST routes."""

from fastapi import FastAPI
from pydantic import ValidationError

from app import services
from app.api.schemas import TradeRequest, normalize_ticker
from app.chat.schema import ChatResponse
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.portfolio import TradeError

MAX_ACTIONS = 10
SKIPPED = f"Skipped: at most {MAX_ACTIONS} actions per reply"
INVALID_TRADE = "Invalid trade (ticker 1-5 letters, quantity > 0, max 4 decimals)"


async def _watchlist(app: FastAPI, source: MarketDataSource, change) -> dict:
    out = {"type": "watchlist", "ticker": change.ticker, "action": change.action}
    try:
        ticker = normalize_ticker(change.ticker)
    except ValueError:
        return {**out, "ok": False, "error": "Invalid ticker (1-5 letters)"}
    out["ticker"] = ticker
    try:
        if change.action == "add":
            await services.add_to_watchlist(app, source, ticker)
        else:
            await services.remove_from_watchlist(app, source, ticker)
    except services.WatchlistError as e:
        return {**out, "ok": False, "error": str(e)}
    return {**out, "ok": True}


async def _trade(app: FastAPI, cache: PriceCache, source: MarketDataSource, trade) -> dict:
    out = {"type": "trade", "ticker": trade.ticker, "side": trade.side, "quantity": trade.quantity}
    try:
        req = TradeRequest(ticker=trade.ticker, side=trade.side, quantity=trade.quantity)
    except ValidationError:
        return {**out, "ok": False, "error": INVALID_TRADE}
    out.update(ticker=req.ticker, quantity=req.quantity)
    try:
        result = await services.place_trade(app, cache, source, req.ticker, req.side, req.quantity)
    except TradeError as e:
        return {**out, "ok": False, "error": str(e)}
    return {**out, "price": result["trade"]["price"], "ok": True}


async def run_actions(
    app: FastAPI, cache: PriceCache, source: MarketDataSource, resp: ChatResponse
) -> list[dict]:
    """Run watchlist changes then trades one at a time, recording each outcome."""
    items = [("w", c) for c in resp.watchlist_changes] + [("t", t) for t in resp.trades]
    out = []
    for i, (kind, item) in enumerate(items):
        if i >= MAX_ACTIONS:
            base = {"type": "watchlist", "ticker": item.ticker}
            if kind == "t":
                base = {"type": "trade", "ticker": item.ticker, "side": item.side, "quantity": item.quantity}
            out.append({**base, "ok": False, "error": SKIPPED})
        elif kind == "w":
            out.append(await _watchlist(app, source, item))
        else:
            out.append(await _trade(app, cache, source, item))
    return out
