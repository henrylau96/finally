"""Deterministic mock responder used when LLM_MOCK=true."""

import os
import re

from app.chat.schema import ChatResponse, TradeAction, WatchlistChange

TRADE = re.compile(r"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+([A-Za-z]{1,5})\b", re.I)
WATCH = re.compile(r"\b(add|remove)\s+([A-Za-z]{1,5})\b", re.I)


def mock_enabled() -> bool:
    """Read LLM_MOCK at call time so tests can toggle it."""
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


def respond(text: str) -> ChatResponse:
    """Parse 'buy 5 AAPL' / 'add PYPL' style phrases into a canned response."""
    trades = [
        TradeAction(ticker=m[3].upper(), side=m[1].lower(), quantity=float(m[2]))
        for m in TRADE.finditer(text)
    ]
    changes = [WatchlistChange(ticker=m[2].upper(), action=m[1].lower()) for m in WATCH.finditer(text)]
    detail = "; ".join(
        [f"{t.side} {t.quantity:g} {t.ticker}" for t in trades]
        + [f"{c.action} {c.ticker}" for c in changes]
    )
    return ChatResponse(
        message=f"Mock response: {detail or 'no actions'}", trades=trades, watchlist_changes=changes
    )
