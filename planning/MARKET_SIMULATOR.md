# Market Simulator

The default price source when `MASSIVE_API_KEY` is not set. It produces realistic-looking, correlated, live prices with no network access and no dependencies beyond `numpy`. Code: `backend/app/market/simulator.py` (engine and data source) and `backend/app/market/seed_prices.py` (parameters). It plugs into the unified interface described in `MARKET_INTERFACE.md`.

## 1. Goals

- Prices tick every **500 ms** and look like a real market: small noisy moves, no mean reversion, prices never negative.
- **Sector correlation**: tech names tend to move together, which makes the heatmap and the AI's analysis more interesting.
- **Drama**: occasional sudden 2 to 5% jumps, so price flashes and P&L swings are visible during a demo.
- Realistic starting prices, and per-ticker volatility (TSLA wild, V calm).
- Any ticker can be added at runtime, including unknown symbols.

## 2. Model: Geometric Brownian Motion

Each tick, every price is multiplied by a log-normal factor:

```
S(t+dt) = S(t) * exp( (mu - sigma^2 / 2) * dt  +  sigma * sqrt(dt) * Z )
```

| Symbol | Meaning |
|---|---|
| `mu` | annualised drift (expected return), e.g. 0.05 |
| `sigma` | annualised volatility, e.g. 0.22 |
| `dt` | tick length as a fraction of a trading year |
| `Z` | standard normal draw, **correlated across tickers** |

Why GBM: it is the standard Black-Scholes price model. It is multiplicative, so prices stay positive. Returns are scale-free, so a $50 stock and an $800 stock move by the same percentage. It needs one line of math per ticker.

### Time step

```
trading seconds per year = 252 days * 6.5 h * 3600 s = 5,896,800
dt = 0.5 / 5,896,800 ≈ 8.48e-8
```

So the simulator runs at "market speed". With this `dt` the move sizes are realistic:

| Ticker | sigma | 1 tick (sd) | 1 hour (sd) | 1 trading day (sd) |
|---|---|---|---|---|
| V | 0.17 | 0.005% (~$0.014) | 0.42% | 1.07% |
| AAPL | 0.22 | 0.006% (~$0.012) | 0.54% | 1.39% |
| TSLA | 0.50 | 0.015% (~$0.036) | 1.24% | 3.15% |

Moves of about one cent per tick make the price flash almost every tick while the sparklines stay plausible. The jump events (section 4) provide the bigger moves.

## 3. Correlated moves (Cholesky)

Independent normals `z` are turned into correlated normals with the Cholesky factor `L` of the correlation matrix `C` (`C = L Lᵀ`):

```
Z = L @ z      # z ~ N(0, I)  ->  Z ~ N(0, C)
```

Pairwise correlation rules (`_pairwise_correlation`):

| Pair | rho |
|---|---|
| tech-tech (AAPL, GOOGL, MSFT, AMZN, META, NVDA, NFLX) | 0.6 |
| finance-finance (JPM, V) | 0.5 |
| anything with TSLA | 0.3 (TSLA "does its own thing") |
| cross-sector / unknown tickers | 0.3 |

This structure is equivalent to a one-factor "market" model (every ticker has 0.3 market correlation) plus extra sector factors. That keeps the matrix positive-definite for any mix of tickers, so `np.linalg.cholesky` never fails. The factor `L` is rebuilt only when tickers are added or removed. That costs O(n³), which is trivial for n < 50. Each tick is a single O(n²) matrix-vector product.

## 4. Random events

After the GBM step, each ticker independently has probability `event_probability = 0.001` per tick of a shock:

```python
if random.random() < self._event_prob:
    shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
    self._prices[ticker] *= 1 + shock
```

With 10 tickers at 2 ticks per second, that is 0.02 events per second, so **about one event every 50 seconds** somewhere in the watchlist. Shocks are permanent: the price does not snap back, as with a news-driven move.

## 5. Parameters (`seed_prices.py`)

```python
SEED_PRICES = {
    "AAPL": 190.00, "GOOGL": 175.00, "MSFT": 420.00, "AMZN": 185.00, "TSLA": 250.00,
    "NVDA": 800.00, "META": 500.00, "JPM": 195.00, "V": 280.00, "NFLX": 600.00,
}

TICKER_PARAMS = {                       # sigma = volatility, mu = drift (annualised)
    "AAPL": {"sigma": 0.22, "mu": 0.05}, "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT": {"sigma": 0.20, "mu": 0.05}, "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA": {"sigma": 0.50, "mu": 0.03}, "NVDA":  {"sigma": 0.40, "mu": 0.08},
    "META": {"sigma": 0.30, "mu": 0.05}, "JPM":   {"sigma": 0.18, "mu": 0.04},
    "V":    {"sigma": 0.17, "mu": 0.04}, "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

DEFAULT_PARAMS = {"sigma": 0.25, "mu": 0.05}   # dynamically added tickers

CORRELATION_GROUPS = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}
INTRA_TECH_CORR, INTRA_FINANCE_CORR, CROSS_GROUP_CORR, TSLA_CORR = 0.6, 0.5, 0.3, 0.3
```

An unknown ticker (for example `PYPL` added via chat) gets a random seed price in `uniform(50, 300)` and `DEFAULT_PARAMS`.

## 6. Engine: `GBMSimulator`

Pure and synchronous, with no asyncio and no cache, so it is easy to unit test.

```python
class GBMSimulator:
    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR

    def __init__(self, tickers: list[str], dt: float = DEFAULT_DT,
                 event_probability: float = 0.001) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None
        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance all tickers one tick. Returns {ticker: price}."""
        n = len(self._tickers)
        if n == 0:
            return {}
        z = np.random.standard_normal(n)
        if self._cholesky is not None:
            z = self._cholesky @ z

        result = {}
        for i, ticker in enumerate(self._tickers):
            mu, sigma = self._params[ticker]["mu"], self._params[ticker]["sigma"]
            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z[i]
            self._prices[ticker] *= math.exp(drift + diffusion)
            if random.random() < self._event_prob:
                self._prices[ticker] *= 1 + random.uniform(0.02, 0.05) * random.choice([-1, 1])
            result[ticker] = round(self._prices[ticker], 2)
        return result

    def add_ticker(self, ticker: str) -> None      # seed + rebuild Cholesky; no-op if present
    def remove_ticker(self, ticker: str) -> None   # drop + rebuild Cholesky; no-op if absent
    def get_price(self, ticker: str) -> float | None
    def get_tickers(self) -> list[str]

    def _rebuild_cholesky(self) -> None:
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return
        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                corr[i, j] = corr[j, i] = self._pairwise_correlation(self._tickers[i], self._tickers[j])
        self._cholesky = np.linalg.cholesky(corr)
```

The engine keeps **full-precision** prices internally and rounds only the values it returns. If it rounded internally, sub-cent drift would be lost.

## 7. Async adapter: `SimulatorDataSource`

Implements `MarketDataSource` by driving the engine from an asyncio task:

```python
class SimulatorDataSource(MarketDataSource):
    def __init__(self, price_cache: PriceCache, update_interval: float = 0.5,
                 event_probability: float = 0.001) -> None: ...

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(tickers=tickers, event_probability=self._event_prob)
        for ticker in tickers:                                 # seed: SSE has data at once
            self._cache.update(ticker, self._sim.get_price(ticker))
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def _run_loop(self) -> None:
        while True:
            try:
                for ticker, price in self._sim.step().items():
                    self._cache.update(ticker, price)
            except Exception:
                logger.exception("Simulator step failed")      # never kill the loop
            await asyncio.sleep(self._interval)

    async def add_ticker(self, ticker: str) -> None:           # price visible immediately
        self._sim.add_ticker(ticker)
        self._cache.update(ticker, self._sim.get_price(ticker))

    async def remove_ticker(self, ticker: str) -> None:
        self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)
```

A step for 10 tickers takes microseconds, so it runs inline on the event loop and needs no thread.

## 8. Known limitations (acceptable for a demo)

- Prices restart from the seed values on every process restart. There is no persistence, and positions are valued at the new simulated price.
- The market runs around the clock: there are no market hours, opening gaps or weekends.
- `PriceCache` rounds to 2 dp, so a tick smaller than half a cent shows as `flat`.
- No intraday volatility smile, no volume. It is price only.

## 9. Testing

Already covered in `backend/tests/market/test_simulator.py` and `test_simulator_source.py`:

- `step()` returns every ticker, positive, rounded to 2 dp. Prices change over time.
- Seed prices are used. Unknown tickers get a random seed price.
- `add_ticker` / `remove_ticker` are idempotent. Cholesky is rebuilt (and is `None` for one ticker).
- Pairwise correlation rules (tech, finance, TSLA, cross-sector).
- Data source: the cache is seeded on `start()`, updates arrive, `stop()` is clean, add/remove reaches the cache, and an exception in `step()` does not kill the loop.

Recommended additions (not yet written):

- Statistical check: with `event_probability=0`, the mean and standard deviation of log-returns match `(mu - sigma²/2)dt` and `sigma*sqrt(dt)`, within tolerance.
- Realised correlation: the sample correlation of tech-pair returns is about 0.6, and cross-sector about 0.3.
- Events: with `event_probability=1.0`, every tick moves by at least 2%.

For deterministic tests, seed both generators: `np.random.seed(0); random.seed(0)`.
