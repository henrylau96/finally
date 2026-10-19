"""Thread-safe in-memory price cache: the single source of truth for prices."""

import threading
import time

from app.market.models import PriceUpdate


class PriceCache:
    """Latest price per ticker plus a version counter for change detection."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._prices: dict[str, PriceUpdate] = {}
        self._opens: dict[str, float] = {}
        self._version = 0

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Store a new price; the first price seen becomes the session open."""
        price = round(price, 2)
        with self._lock:
            prev = self._prices.get(ticker)
            open_price = self._opens.setdefault(ticker, price)
            update = PriceUpdate(
                ticker=ticker,
                price=price,
                previous_price=prev.price if prev else price,
                timestamp=timestamp if timestamp is not None else time.time(),
                session_open=open_price,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        with self._lock:
            return dict(self._prices)

    def remove(self, ticker: str) -> None:
        with self._lock:
            self._prices.pop(ticker, None)
            self._opens.pop(ticker, None)
            self._version += 1

    @property
    def version(self) -> int:
        return self._version
