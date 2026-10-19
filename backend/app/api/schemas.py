"""Request types shared by the watchlist and portfolio endpoints."""

import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field


def normalize_ticker(v: str) -> str:
    """Trim, uppercase and require 1-5 letters."""
    v = v.strip().upper()
    if not re.fullmatch(r"[A-Z]{1,5}", v):
        raise ValueError("ticker must be 1-5 letters")
    return v


def four_dp(v: float) -> float:
    """Accept float noise around at most 4 decimals and round to 4."""
    if abs(v * 1e4 - round(v * 1e4)) >= 1e-6:
        raise ValueError("quantity allows at most 4 decimals")
    return round(v, 4)


Ticker = Annotated[str, AfterValidator(normalize_ticker)]
Quantity = Annotated[
    float,
    Field(strict=True, gt=0, le=1_000_000, allow_inf_nan=False),
    AfterValidator(four_dp),
]


class TradeRequest(BaseModel):
    ticker: Ticker
    side: Literal["buy", "sell"]
    quantity: Quantity
