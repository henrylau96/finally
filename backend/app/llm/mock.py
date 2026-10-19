"""Deterministic mock LLM used when LLM_MOCK=true."""

import re

from .schema import ChatResponse, TradeAction, WatchlistAction

TRADE_RE = re.compile(r"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+([A-Za-z.]{1,10})\b", re.IGNORECASE)
WATCH_RE = re.compile(r"\b(add|remove)\s+([A-Za-z.]{1,10})\b", re.IGNORECASE)


def mock_response(message: str) -> ChatResponse:
    """Parse buy/sell/add/remove commands from the user message."""
    trades = [
        TradeAction(side=side.lower(), quantity=float(qty), ticker=ticker.upper())
        for side, qty, ticker in TRADE_RE.findall(message)
    ]
    changes = [
        WatchlistAction(action=action.lower(), ticker=ticker.upper())
        for action, ticker in WATCH_RE.findall(message)
    ]
    parts = [f"{t.side} {t.quantity:g} {t.ticker}" for t in trades]
    parts += [f"{c.action} {c.ticker}" for c in changes]
    summary = ", ".join(parts) or "no actions"
    return ChatResponse(
        message=f"Mock response: {summary}", trades=trades, watchlist_changes=changes
    )
