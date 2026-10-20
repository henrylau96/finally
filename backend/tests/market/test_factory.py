from app.market import MassiveDataSource, PriceCache, SimulatorDataSource, create_market_data_source


def test_factory_simulator_when_key_empty(monkeypatch):
    """An empty key selects the simulator."""
    monkeypatch.setenv("MASSIVE_API_KEY", "")
    assert isinstance(create_market_data_source(PriceCache()), SimulatorDataSource)


def test_factory_simulator_when_key_whitespace(monkeypatch):
    """A whitespace key selects the simulator."""
    monkeypatch.setenv("MASSIVE_API_KEY", "  ")
    assert isinstance(create_market_data_source(PriceCache()), SimulatorDataSource)


def test_factory_simulator_when_key_unset(monkeypatch):
    """No key selects the simulator."""
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    assert isinstance(create_market_data_source(PriceCache()), SimulatorDataSource)


def test_factory_massive_when_key_set(monkeypatch):
    """A key selects Massive with a 15 s default interval or MASSIVE_POLL_INTERVAL."""
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.delenv("MASSIVE_POLL_INTERVAL", raising=False)
    source = create_market_data_source(PriceCache())
    assert isinstance(source, MassiveDataSource)
    assert source._interval == 15.0
    monkeypatch.setenv("MASSIVE_POLL_INTERVAL", "30")
    assert create_market_data_source(PriceCache())._interval == 30.0


def test_factory_massive_client_does_not_retry(monkeypatch):
    """The Massive client makes no SDK retries, which would burn the free-tier quota."""
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    assert create_market_data_source(PriceCache())._client.retries == 0
