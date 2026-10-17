# Unified Market Data Interface

How FinAlly gets stock prices. One Python API is used everywhere. Behind it is either the **Massive REST API** (when `MASSIVE_API_KEY` is set) or the **GBM simulator** (the default). Code lives in `backend/app/market/`. See `MASSIVE_API.md` for the API itself and `MARKET_SIMULATOR.md` for the simulator.

## 1. Design

```
                 create_market_data_source(cache)        reads MASSIVE_API_KEY
                              |
             +----------------+-----------------+
             |                                  |
   SimulatorDataSource                  MassiveDataSource
   (GBM, 500 ms ticks)                  (REST poll: snapshot or EOD)
             |                                  |
             +------------> PriceCache <--------+      writers (exactly one)
                                |
          +---------------------+---------------------+
          |                     |                     |
   SSE /api/stream/prices   portfolio valuation   trade execution   readers
```

Principles:

- **Push into a cache, read from the cache.** Data sources run their own background task and write to `PriceCache`. Downstream code never calls a data source to get a price. It reads `cache.get_price(ticker)`, so reads are always instant and never touch the network.
- **One interface, two strategies.** Both sources implement the `MarketDataSource` ABC. Only the factory knows which one is active.
- **Ticker set is driven by the watchlist.** The API layer calls `add_ticker` and `remove_ticker` when the watchlist changes.

## 2. Public API

```python
from app.market import (
    PriceUpdate,                # immutable price snapshot
    PriceCache,                 # thread-safe latest-price store
    MarketDataSource,           # ABC
    create_market_data_source,  # factory
    create_stream_router,       # FastAPI SSE router factory
)
```

### 2.1 `PriceUpdate` (`models.py`)

```python
@dataclass(frozen=True, slots=True)
class PriceUpdate:
    ticker: str
    price: float
    previous_price: float
    timestamp: float            # Unix seconds

    change: float               # property: price - previous_price
    change_percent: float       # property
    direction: str              # property: "up" | "down" | "flat"

    def to_dict(self) -> dict: ...   # JSON/SSE payload
```

### 2.2 `PriceCache` (`cache.py`)

```python
class PriceCache:
    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate
    def get(self, ticker: str) -> PriceUpdate | None
    def get_price(self, ticker: str) -> float | None
    def get_all(self) -> dict[str, PriceUpdate]   # shallow copy
    def remove(self, ticker: str) -> None
    version: int                                  # bumps on every update
```

- `update()` takes the previous price from the existing entry, so sources only supply the new price. The first update for a ticker is `flat`.
- Prices are rounded to 2 dp.
- A `threading.Lock` makes it safe even when the Massive SDK runs in a worker thread.
- `version` lets SSE skip sending when nothing has changed.

### 2.3 `MarketDataSource` (`interface.py`)

```python
class MarketDataSource(ABC):
    async def start(self, tickers: list[str]) -> None    # seed cache, launch background task
    async def stop(self) -> None                         # cancel task; idempotent
    async def add_ticker(self, ticker: str) -> None      # no-op if present
    async def remove_ticker(self, ticker: str) -> None   # also removes from cache
    def get_tickers(self) -> list[str]
```

Contract:

- `start()` must leave the cache populated (or try to) before it returns, so the first SSE event has data.
- Errors inside the background loop are logged and never raised. One failed poll must not kill the stream.
- Tickers are upper-case symbols. Normalise them at the API boundary.

### 2.4 Factory (`factory.py`)

```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    return SimulatorDataSource(price_cache=price_cache)
```

An empty or whitespace-only key means the simulator is used.

### 2.5 SSE router (`stream.py`)

`create_stream_router(cache)` returns an `APIRouter` with `GET /api/stream/prices`. Every 500 ms, if `cache.version` changed, it sends one event containing all tickers:

```
retry: 1000

data: {"AAPL": {"ticker": "AAPL", "price": 190.52, "previous_price": 190.48, "timestamp": 1760790000.5,
                "change": 0.04, "change_percent": 0.021, "direction": "up"}, "MSFT": {...}}
```

## 3. Wiring into FastAPI

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import PriceCache, create_market_data_source, create_stream_router

cache = PriceCache()
source = create_market_data_source(cache)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await source.start(load_watchlist_tickers())   # from SQLite
    yield
    await source.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(create_stream_router(cache))
```

Watchlist endpoints keep the source in sync:

```python
@app.post("/api/watchlist")
async def add_watch(body: AddTicker):
    ticker = body.ticker.upper().strip()
    db_add_watchlist(ticker)
    await source.add_ticker(ticker)

@app.delete("/api/watchlist/{ticker}")
async def remove_watch(ticker: str):
    ticker = ticker.upper().strip()
    db_remove_watchlist(ticker)
    if not db_has_position(ticker):         # keep pricing tickers we still hold
        await source.remove_ticker(ticker)
```

Trades read the cache:

```python
price = cache.get_price(ticker)
if price is None:
    raise HTTPException(400, f"No price available for {ticker}")
```

The tracked set should be **watchlist ∪ held positions**. Otherwise a held ticker removed from the watchlist loses its price and the portfolio cannot be valued.

## 4. `SimulatorDataSource`

A thin async wrapper around `GBMSimulator` (see `MARKET_SIMULATOR.md`):

- `start()` builds the simulator, writes the seed prices to the cache, and launches a loop that calls `sim.step()` every 0.5 s and writes each price.
- `add_ticker()` adds the ticker to the simulator and writes its seed price to the cache straight away, so the UI shows a price instantly.

## 5. `MassiveDataSource`

Polls Massive on an interval. Its key job is to **work on every plan** (see `MASSIVE_API.md` section 2):

| Mode | Endpoint | When | Interval |
|---|---|---|---|
| `snapshot` | `get_snapshot_all(STOCKS, tickers=...)` | Starter+ keys | 15 s (default) |
| `eod` | `get_grouped_daily_aggs(date)` | Free keys (snapshot returns 403 `NOT_AUTHORIZED`) | 15 min |

The source starts in `snapshot` mode. If the first snapshot call is rejected as not authorised, it switches to `eod` permanently and logs a warning once. Both modes use a single API call per poll whatever the number of tickers.

### 5.1 Price extraction

A pure function that is easy to test with real SDK models:

```python
def snapshot_price(snap: TickerSnapshot) -> tuple[float, float | None] | None:
    """Best available (price, unix_seconds) from a snapshot, or None."""
    if snap.last_trade and snap.last_trade.price:
        return snap.last_trade.price, snap.last_trade.sip_timestamp / 1e9   # ns
    if snap.min and snap.min.close:
        return snap.min.close, snap.min.timestamp / 1e3                     # ms
    if snap.day and snap.day.close:
        return snap.day.close, None
    if snap.prev_day and snap.prev_day.close:
        return snap.prev_day.close, None
    return None
```

`last_trade` is `None` on Starter (no trades entitlement), and `day.close` is `0` before the open. This fallback chain handles both.

### 5.2 Poll loop

```python
from massive import RESTClient
from massive.exceptions import BadResponse
from massive.rest.models import SnapshotMarketType

class MassiveDataSource(MarketDataSource):
    def __init__(self, api_key: str, price_cache: PriceCache,
                 poll_interval: float = 15.0, eod_poll_interval: float = 900.0) -> None:
        self._client = RESTClient(api_key=api_key)
        self._cache = price_cache
        self._interval = poll_interval
        self._eod_interval = eod_poll_interval
        self._mode = "snapshot"
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._tickers = [t.upper() for t in tickers]
        await self._poll_once()                       # fill cache before first SSE
        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        if not self._tickers:
            return
        try:
            prices = await asyncio.to_thread(self._fetch)    # SDK is synchronous
        except BadResponse as e:
            if self._mode == "snapshot" and "NOT_AUTHORIZED" in str(e):
                logger.warning("Massive plan has no snapshots; using end-of-day prices")
                self._mode, self._interval = "eod", self._eod_interval
                return await self._poll_once()
            logger.error("Massive poll failed: %s", e)
            return
        except Exception as e:                               # network etc.
            logger.error("Massive poll failed: %s", e)
            return
        for ticker, (price, ts) in prices.items():
            self._cache.update(ticker, price, ts)

    def _fetch(self) -> dict[str, tuple[float, float | None]]:
        if self._mode == "snapshot":
            snaps = self._client.get_snapshot_all(SnapshotMarketType.STOCKS, tickers=self._tickers)
            return {s.ticker: p for s in snaps if (p := snapshot_price(s))}
        self._eod_closes = latest_eod_closes(self._client)        # all US stocks, MASSIVE_API.md 3.3
        return {t: (self._eod_closes[t], None) for t in self._tickers if t in self._eod_closes}
```

`add_ticker` and `remove_ticker` only change `self._tickers` (and `remove_ticker` also clears the cache entry). In snapshot mode a newly added ticker gets its price on the next poll (at most 15 s). In EOD mode the last grouped response already holds every US stock, so `add_ticker` prices the new ticker at once from `self._eod_closes`, with no API call.

### 5.3 Testing guidance

Build fixtures from **real SDK models**, not `MagicMock`:

```python
from massive.rest.models import TickerSnapshot

snap = TickerSnapshot.from_dict({
    "ticker": "AAPL",
    "lastTrade": {"p": 190.5, "t": 1760790000000000000},
    "min": {"c": 190.4, "t": 1760790000000},
    "prevDay": {"c": 188.0},
})
assert snapshot_price(snap) == (190.5, 1760790000.0)
```

A `MagicMock` accepts any attribute name, so it hides field-name mistakes. For example, `last_trade.timestamp` does not exist on the real `LastTrade` model.

Cases to cover: Developer payload (with `lastTrade`), Starter payload (no `lastTrade`), pre-market (`day.c == 0`), empty snapshot, the `BadResponse` `NOT_AUTHORIZED` fallback to EOD, and grouped daily stepping back past a weekend.

## 6. Behaviour summary

| `MASSIVE_API_KEY` | Source | Update cadence | Price meaning |
|---|---|---|---|
| unset / empty | Simulator | 500 ms | Simulated GBM |
| free key | Massive `eod` | 15 min | Last trading day's close (static) |
| Starter / Developer | Massive `snapshot` | 15 s | 15-min delayed |
| Advanced | Massive `snapshot` | 15 s (can be 2 to 5 s) | Real-time |

In every case the SSE stream keeps sending every 500 ms whenever `cache.version` changes. The frontend does not know which source is running.
