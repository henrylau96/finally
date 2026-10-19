"""Selects the market data source for the app."""

from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.market.simulator_source import SimulatorDataSource


def create_market_data_source(cache: PriceCache) -> MarketDataSource:
    """Return the simulator (Massive selection arrives in Phase 5)."""
    return SimulatorDataSource(cache)
