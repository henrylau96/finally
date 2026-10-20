import numpy as np

from app.market.seed_prices import DEFAULT_TICKERS, SEED_PRICES
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


def _log_returns(sim, steps):
    """Collect per-step log returns as an array of shape (steps-1, n_tickers)."""
    rows = [list(sim.step().values()) for _ in range(steps)]
    return np.diff(np.log(np.array(rows)), axis=0)


def test_seed_prices_all_defaults():
    """Every default ticker starts at its seed price."""
    sim = GBMSimulator(DEFAULT_TICKERS, seed=1)
    assert all(sim.get_price(t) == SEED_PRICES[t] for t in DEFAULT_TICKERS)


def test_seed_price_unknown_ticker_in_range():
    """An unknown ticker starts between 50 and 300."""
    assert 50 <= GBMSimulator(["ZZZZ"], seed=1).get_price("ZZZZ") <= 300


def test_gbm_log_return_moments():
    """Sample mean and std of log returns match the GBM parameters."""
    dt, n = 1e-4, 20000
    sigma, mu = 0.22, 0.05
    r = _log_returns(GBMSimulator(["AAPL"], dt=dt, event_probability=0.0, seed=42), n)[:, 0]
    expected = (mu - sigma**2 / 2) * dt
    assert abs(r.mean() - expected) < 4 * sigma * np.sqrt(dt) / np.sqrt(n)
    assert abs(r.std() / (sigma * np.sqrt(dt)) - 1) < 0.05


def test_correlation_matches_groups():
    """Realised correlations follow the tech / finance / cross-sector rules."""
    r = _log_returns(GBMSimulator(DEFAULT_TICKERS, dt=1e-4, event_probability=0.0, seed=7), 20000)
    c = np.corrcoef(r.T)
    idx = {t: i for i, t in enumerate(DEFAULT_TICKERS)}
    assert abs(c[idx["AAPL"], idx["GOOGL"]] - 0.6) < 0.05
    assert abs(c[idx["JPM"], idx["V"]] - 0.5) < 0.05
    assert abs(c[idx["AAPL"], idx["JPM"]] - 0.3) < 0.05
    assert abs(c[idx["TSLA"], idx["AAPL"]] - 0.3) < 0.05


def test_correlation_cholesky_factor():
    """Cholesky exists for the defaults and is None for a single ticker."""
    assert GBMSimulator(DEFAULT_TICKERS, seed=1)._cholesky is not None
    assert GBMSimulator(["AAPL"], seed=1)._cholesky is None


def test_event_moves_every_ticker():
    """With event probability 1 every ticker jumps 2-5%."""
    sim = GBMSimulator(DEFAULT_TICKERS, dt=1e-12, event_probability=1.0, seed=3)
    before = [sim.get_price(t) for t in DEFAULT_TICKERS]
    after = list(sim.step().values())
    moves = np.abs(np.log(np.array(after) / np.array(before)))
    assert moves.min() >= 0.019
    assert moves.max() <= 0.052


def test_add_remove_ticker():
    """Tickers can be added and removed while stepping."""
    sim = GBMSimulator(["AAPL", "MSFT"], seed=1)
    sim.add_ticker("PYPL")
    assert "PYPL" in sim.tickers and 50 <= sim.get_price("PYPL") <= 300
    assert "PYPL" in sim.step()
    before = sim.tickers
    sim.add_ticker("PYPL")
    assert sim.tickers == before
    sim.remove_ticker("PYPL")
    assert "PYPL" not in sim.tickers
    assert "PYPL" not in sim.step()
