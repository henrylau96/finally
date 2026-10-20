"""Selects the market data source for the app."""

import os

from massive import RESTClient

from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.market.massive_source import MassiveDataSource
from app.market.simulator_source import SimulatorDataSource


def create_market_data_source(cache: PriceCache) -> MarketDataSource:
    """Massive when MASSIVE_API_KEY is non-empty, else the simulator."""
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if not key:
        return SimulatorDataSource(cache)
    interval = float(os.environ.get("MASSIVE_POLL_INTERVAL", "").strip() or 15)
    client = RESTClient(api_key=key, retries=0, connect_timeout=5.0, read_timeout=5.0)
    return MassiveDataSource(cache, client, interval)
