"""Chat request and (lenient) LLM response models; actions are re-validated before execution."""

from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints


class TradeAction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class ChatResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
