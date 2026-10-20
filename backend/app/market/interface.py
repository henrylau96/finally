"""Abstract market data source shared by the simulator and real-data clients."""

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Produces price updates into a PriceCache for a dynamic set of tickers.

    `name` labels the source (e.g. "simulator", "massive").
    """

    name: str

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing prices for the given tickers."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop producing prices; safe to call repeatedly."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Start tracking a ticker."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop tracking a ticker and drop it from the cache."""

    @abstractmethod
    async def history(self, ticker: str) -> list[dict]:
        """Recent daily closes as ascending {time, value} points (time in seconds); empty when the source has none."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the currently tracked tickers."""
