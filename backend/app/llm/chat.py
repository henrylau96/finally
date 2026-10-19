"""Chat orchestration: context, LLM call, action execution, persistence."""

import logging
import os

from app import db
from app.market import MarketDataSource, PriceCache
from app.portfolio import (
    TradeError,
    add_watchlist_ticker,
    execute_trade,
    get_portfolio,
    get_watchlist_with_prices,
    remove_watchlist_ticker,
)

from .client import call_llm
from .mock import mock_response
from .prompt import build_messages
from .schema import ChatResponse, TradeAction, WatchlistAction

HISTORY_LIMIT = 20
UNAVAILABLE_MESSAGE = "Sorry, the AI service is unavailable right now. Please try again."

logger = logging.getLogger(__name__)


def is_mock() -> bool:
    """Return True when LLM_MOCK is enabled."""
    return os.getenv("LLM_MOCK", "false").strip().lower() == "true"


def run_trade(trade: TradeAction, price_cache: PriceCache, user_id: str) -> dict:
    """Execute one trade and return its result entry."""
    result = {"ticker": trade.ticker.upper(), "side": trade.side, "quantity": trade.quantity,
              "status": "executed", "price": None, "error": None}
    try:
        result["price"] = execute_trade(
            trade.ticker, trade.side, trade.quantity, price_cache, user_id
        )["price"]
    except TradeError as e:
        result.update(status="failed", error=str(e))
    return result


async def run_watchlist_change(
    change: WatchlistAction, source: MarketDataSource, user_id: str
) -> dict:
    """Apply one watchlist change and return its result entry."""
    ticker = change.ticker.upper()
    result = {"ticker": ticker, "action": change.action, "status": "executed", "error": None}
    try:
        if change.action == "add":
            ok = await add_watchlist_ticker(ticker, source, user_id)
            error = f"{ticker} is already in the watchlist"
        else:
            ok = await remove_watchlist_ticker(ticker, source, user_id)
            error = f"{ticker} is not in the watchlist"
    except ValueError as e:
        ok, error = False, str(e)
    if not ok:
        result.update(status="failed", error=error)
    return result


async def get_response(message: str, price_cache: PriceCache, user_id: str) -> ChatResponse:
    """Return the mock response or call the real LLM with full context."""
    if is_mock():
        return mock_response(message)
    messages = build_messages(
        message,
        get_portfolio(price_cache, user_id),
        get_watchlist_with_prices(price_cache, user_id),
        db.get_chat_messages(user_id, limit=HISTORY_LIMIT),
    )
    try:
        return await call_llm(messages)
    except Exception:
        logger.exception("LLM call failed")
        return ChatResponse(message=UNAVAILABLE_MESSAGE)


async def handle_chat(
    message: str, price_cache: PriceCache, market_source: MarketDataSource,
    user_id: str = "default",
) -> dict:
    """Handle a user chat message end to end and return the POST /api/chat body."""
    response = await get_response(message, price_cache, user_id)
    db.add_chat_message("user", message, None, user_id)
    trades = [run_trade(t, price_cache, user_id) for t in response.trades]
    changes = [
        await run_watchlist_change(c, market_source, user_id) for c in response.watchlist_changes
    ]
    actions = {"trades": trades, "watchlist_changes": changes}
    db.add_chat_message("assistant", response.message, actions, user_id)
    return {"message": response.message, **actions}
