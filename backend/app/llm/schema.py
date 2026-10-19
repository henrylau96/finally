"""Structured output schema for LLM chat responses."""

from typing import Literal

from pydantic import BaseModel, Field


class TradeAction(BaseModel):
    """A trade the assistant wants to execute."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistAction(BaseModel):
    """A watchlist change the assistant wants to make."""

    ticker: str
    action: Literal["add", "remove"]


class ChatResponse(BaseModel):
    """The full structured response returned by the LLM."""

    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistAction] = Field(default_factory=list)
