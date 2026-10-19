"""Price update value object."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """One ticker's latest price with change context."""

    ticker: str
    price: float
    previous_price: float
    timestamp: float
    session_open: float

    @property
    def direction(self) -> Literal["up", "down", "flat"]:
        if self.price > self.previous_price:
            return "up"
        if self.price < self.previous_price:
            return "down"
        return "flat"

    @property
    def day_change_pct(self) -> float:
        return round((self.price - self.session_open) / self.session_open * 100, 2)

    def to_dict(self) -> dict:
        """Serialize to the six-key SSE contract."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "direction": self.direction,
            "day_change_pct": self.day_change_pct,
        }
