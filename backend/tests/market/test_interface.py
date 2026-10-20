import pytest

from app.market import MarketDataSource, PriceCache, SimulatorDataSource, create_market_data_source


def test_interface_is_abstract():
    """The ABC cannot be instantiated."""
    with pytest.raises(TypeError):
        MarketDataSource()


def test_simulator_source_conforms():
    """SimulatorDataSource implements the interface."""
    assert isinstance(SimulatorDataSource(PriceCache()), MarketDataSource)


async def test_simulator_history_is_empty():
    """The simulator has no history to seed."""
    assert await SimulatorDataSource(PriceCache()).history("AAPL") == []


def test_factory_returns_simulator():
    """The factory defaults to the simulator."""
    assert isinstance(create_market_data_source(PriceCache()), SimulatorDataSource)
