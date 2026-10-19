from app.market.seed_prices import DEFAULT_TICKERS
from app.market.simulator import GBMSimulator


def test_step_returns_valid_rounded_prices():
    """Every step returns all tickers with positive 2 dp prices."""
    prices = GBMSimulator(DEFAULT_TICKERS, seed=1).step()
    assert set(prices) == set(DEFAULT_TICKERS)
    assert all(p > 0 and p == round(p, 2) for p in prices.values())


def test_prices_move():
    """Prices change over repeated steps."""
    sim = GBMSimulator(DEFAULT_TICKERS, seed=1)
    first = sim.step()
    last = first
    for _ in range(20):
        last = sim.step()
    assert last != first


def test_seed_price():
    """AAPL starts at its seed price."""
    assert GBMSimulator(DEFAULT_TICKERS, seed=1).get_price("AAPL") == 190.0
