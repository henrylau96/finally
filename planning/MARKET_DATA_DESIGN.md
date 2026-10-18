# Market Data Backend — Detailed Design

Implementation design for the FinAlly market data layer: the unified API, the GBM simulator, the Massive (Polygon.io) client, the SSE stream, and how the rest of the backend plugs into them.

This document is grounded in the code that already exists in `backend/app/market/` (84 tests passing). Each section says whether it describes **built** code or a **proposed** change, and every proposed change comes with the code to implement it. The proposed snippets and tests in sections 4 to 13 were applied to a scratch copy of the backend: the existing 84 tests plus the new tests in section 13 all pass (102 total). Where the code and `PLAN.md` disagree, section 2 lists the difference and the fix.

Companion references (read only when you need the detail):

| Doc | Use it for |
|---|---|
| `PLAN.md` §6, §8, §10 | The product contract this layer serves |
| `MARKET_INTERFACE.md` | Short reference card for the public API |
| `MARKET_SIMULATOR.md` | GBM maths, parameter tables, move-size calculations |
| `MASSIVE_API.md` | Massive plans, endpoints, SDK models, timestamp units, SDK bugs |
| `MARKET_DATA_SUMMARY.md` | What was built and reviewed |
| `archive/` | Earlier drafts and the code review; superseded by this document |

---

## Contents

1. [Architecture](#1-architecture)
2. [Plan vs. code: gaps and decisions](#2-plan-vs-code-gaps-and-decisions)
3. [Module layout](#3-module-layout)
4. [Unified API](#4-unified-api)
5. [Simulator](#5-simulator)
6. [Massive API client](#6-massive-api-client)
7. [Factory and configuration](#7-factory-and-configuration)
8. [SSE stream](#8-sse-stream)
9. [Tracked tickers: watchlist ∪ positions](#9-tracked-tickers-watchlist--positions)
10. [FastAPI integration](#10-fastapi-integration)
11. [Frontend contract](#11-frontend-contract)
12. [Error handling and edge cases](#12-error-handling-and-edge-cases)
13. [Testing](#13-testing)
14. [Implementation checklist](#14-implementation-checklist)

---

## 1. Architecture

```
                      create_market_data_source(cache)     reads MASSIVE_API_KEY
                                   │
                 ┌─────────────────┴──────────────────┐
                 │                                    │
       SimulatorDataSource                    MassiveDataSource
       GBMSimulator, 500 ms ticks             REST poll: snapshot (15 s) or EOD (15 min)
                 │                                    │
                 └──────────────► PriceCache ◄────────┘     exactly one writer
                                     │
        ┌──────────────┬─────────────┼──────────────┬──────────────────┐
        │              │             │              │                  │
  SSE stream     GET /api/watchlist  portfolio     trade execution    LLM chat context
  /api/stream/   (latest prices)     valuation +   (fill price)       (prices in prompt)
  prices                             snapshots
```

Three rules hold the design together:

1. **Sources push, everyone else reads the cache.** A data source owns one background task that writes to `PriceCache`. No route ever calls a data source to get a price, so every price read is a dict lookup that never touches the network.
2. **One interface, two strategies.** `SimulatorDataSource` and `MassiveDataSource` both implement the `MarketDataSource` ABC. Only the factory knows which one runs. The frontend cannot tell either.
3. **The backend decides which tickers are tracked.** The tracked set is *watchlist ∪ held positions* (section 9). It is reconciled by one helper after any watchlist change or trade, whether the change came from the UI or from the LLM.

---

## 2. Plan vs. code: gaps and decisions

The built code matches `PLAN.md` §6 on every structural point (ABC, two sources, shared cache, SSE at ~500 ms, env-var switch, free-tier EOD fallback). These are the places where it does not yet cover what the rest of the plan needs, with the decision this document takes.

| # | Plan says | Code today | Decision (section) |
|---|---|---|---|
| G1 | Watchlist shows **daily change %** (§10) | `change_percent` is tick-to-tick; there is no daily reference price | Add `reference_price` to `PriceUpdate`/`PriceCache` and `day_change_percent` to the payload (§4.3) |
| G2 | Held positions must be valued (§7, §8) | `remove_ticker` drops the price from the cache; nothing keeps held tickers tracked | Track watchlist ∪ positions via one `sync_tracked_tickers()` helper (§9) |
| G3 | SSE resilience (§12) | No keep-alive; on a free key the stream can be silent for 15 min, and idle proxies drop it | Send a `: ping` comment every 15 s with no data (§8.3) |
| G4 | — | `stream.py` registers the route on a module-level `router`, so calling `create_stream_router()` twice registers `/prices` twice (review item 3.6) | Create the router inside the factory (§8.2) |
| G5 | "add tickers via chat" then trade at once | On Massive snapshot mode a new ticker has no price for up to 15 s, so an immediate trade fails | Trigger one coalesced refresh poll on `add_ticker` (§6.5) |
| G6 | — | `_fetch` reads `self._tickers` in a worker thread while `add_ticker` can mutate it on the loop | Pass a copy of the ticker list into the thread (§6.5) |
| G7 | Tickers are upper-case symbols | `MassiveDataSource` normalises; `SimulatorDataSource` does not | Normalise and validate once at the API boundary with `normalize_ticker()` (§9.1) |
| G8 | Plan streams "all tickers known to the system" | Same; with G2 this includes held tickers not on the watchlist | Frontend renders the watchlist from `GET /api/watchlist` and uses SSE only as a price feed (§11) |

Things deliberately **not** changed:

- **One SSE event carries all tickers** (`{"AAPL": {...}, "MSFT": {...}}`) rather than one event per ticker. Each entry carries everything the plan lists (ticker, price, previous price, timestamp, direction). One event per tick is cheaper to parse and keeps the sparklines aligned.
- **REST polling, not Massive WebSockets.** Works with every key, including free ones, and fits the cache model (`MASSIVE_API.md` §3.8).
- **2 dp rounding in the cache.** Sub-cent simulator ticks show as `flat`. This is acceptable and keeps the payload and the UI clean.
- **Poll intervals are constructor arguments, not env vars.** `PLAN.md` §5 lists only three env vars; adding `MASSIVE_POLL_INTERVAL` is easy (§7) but not required.

---

## 3. Module layout

```
backend/app/market/
├── __init__.py          built      re-exports the public API
├── models.py            built      PriceUpdate                      (+ reference_price, G1)
├── cache.py             built      PriceCache                       (+ reference_price, G1)
├── interface.py         built      MarketDataSource ABC
├── seed_prices.py       built      seed prices, GBM params, correlation groups
├── simulator.py         built      GBMSimulator + SimulatorDataSource (+ reference, G1)
├── massive_client.py    built      MassiveDataSource + pure helpers   (+ G1, G5, G6)
├── factory.py           built      create_market_data_source()
├── stream.py            built      create_stream_router()             (+ G3, G4)
└── tracking.py          proposed   normalize_ticker(), sync_tracked_tickers()  (G2, G7)
```

Everything outside `app/market/` imports from the package root:

```python
from app.market import (
    PriceUpdate, PriceCache, MarketDataSource,
    create_market_data_source, create_stream_router,
    normalize_ticker, sync_tracked_tickers,          # proposed, section 9
)
```

---

## 4. Unified API

### 4.1 `MarketDataSource` (built, `interface.py`)

```python
class MarketDataSource(ABC):
    @abstractmethod
    async def start(self, tickers: list[str]) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    async def add_ticker(self, ticker: str) -> None: ...
    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None: ...
    @abstractmethod
    def get_tickers(self) -> list[str]: ...
```

Contract every implementation honours:

| Method | Must | Must not |
|---|---|---|
| `start(tickers)` | Try to populate the cache before returning, so the first SSE event has data; launch one background task | Raise on a failed first fetch (log it; the loop retries) |
| `stop()` | Cancel the task and await it; be safe to call twice | Write to the cache afterwards |
| `add_ticker(t)` | Be a no-op if already tracked; get a price into the cache as soon as it can | Block on the network inside the event loop |
| `remove_ticker(t)` | Be a no-op if absent; remove `t` from the cache | — |
| background loop | Catch and log every exception, then keep going | Ever let one bad tick or poll kill the stream |

Tickers passed in are already upper-case and validated (section 9.1).

### 4.2 `PriceUpdate` (built, `models.py`)

```python
@dataclass(frozen=True, slots=True)
class PriceUpdate:
    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)   # Unix seconds

    change: float          # property: price - previous_price (4 dp)
    change_percent: float  # property: tick-to-tick %, 0.0 if previous_price == 0
    direction: str         # property: "up" | "down" | "flat"
    def to_dict(self) -> dict: ...
```

Immutable, so it is safe to hand the same object to many SSE clients and routes. Derived fields are properties, so they can never disagree with `price`.

### 4.3 Daily change: `reference_price` (proposed, G1)

The watchlist needs "daily change %", which is the move against a reference price, not against the previous tick. The reference depends on the source:

| Source | `reference_price` | Meaning in the UI |
|---|---|---|
| Simulator | Seed price when the ticker started being tracked | Change since the session started |
| Massive snapshot | `prev_day.close` | Change since yesterday's close (matches `todaysChangePerc`) |
| Massive EOD | That bar's `open` | The last trading day's open-to-close move |

`models.py`, add one field with a default (existing constructors and tests keep working) and two properties:

```python
@dataclass(frozen=True, slots=True)
class PriceUpdate:
    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)
    reference_price: float | None = None   # daily-change baseline; None = unknown

    # ... change, change_percent, direction unchanged ...

    @property
    def day_change(self) -> float:
        if self.reference_price is None:
            return 0.0
        return round(self.price - self.reference_price, 4)

    @property
    def day_change_percent(self) -> float:
        if not self.reference_price:
            return 0.0
        return round((self.price - self.reference_price) / self.reference_price * 100, 4)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
            "reference_price": self.reference_price,
            "day_change": self.day_change,
            "day_change_percent": self.day_change_percent,
        }
```

### 4.4 `PriceCache` (built, `cache.py`; proposed `reference_price` argument)

Built behaviour:

- `update(ticker, price, timestamp=None) -> PriceUpdate` takes the previous price from the existing entry, so sources only supply the new price. The first update for a ticker is `flat`.
- `get`, `get_price`, `get_all` (shallow copy), `remove`, `__len__`, `__contains__`.
- `version` is a monotonic counter bumped on every `update()`; SSE uses it to skip identical pushes.
- A `threading.Lock` guards the dict, because the Massive SDK runs in a worker thread.

Proposed change: an optional `reference_price` that **sticks**. A source passes it when it knows it (Massive) or once at seed time (simulator); later updates without it keep the stored value. The default is the first price seen, so a source that never passes one still gets "change since first seen".

```python
def update(
    self,
    ticker: str,
    price: float,
    timestamp: float | None = None,
    reference_price: float | None = None,
) -> PriceUpdate:
    with self._lock:
        ts = timestamp or time.time()
        prev = self._prices.get(ticker)
        previous_price = prev.price if prev else price
        if reference_price is None:
            reference_price = prev.reference_price if prev else price

        update = PriceUpdate(
            ticker=ticker,
            price=round(price, 2),
            previous_price=round(previous_price, 2),
            timestamp=ts,
            reference_price=round(reference_price, 2),
        )
        self._prices[ticker] = update
        self._version += 1
        return update

@property
def version(self) -> int:
    with self._lock:          # review item 3.4: consistent with the rest of the class
        return self._version
```

Example:

```python
cache = PriceCache()
cache.update("AAPL", 190.00)                       # flat, reference 190.00
u = cache.update("AAPL", 191.90)
u.direction, u.change, u.day_change_percent        # ("up", 1.9, 1.0)
cache.update("AAPL", 191.50, reference_price=189.00).day_change   # 2.5
cache.update("AAPL", 191.60).reference_price       # 189.0 (sticky)
```

---

## 5. Simulator

Built; the maths and parameters are documented in `MARKET_SIMULATOR.md` and not repeated here. This section covers how it is structured and the one proposed change.

### 5.1 Two layers

```
GBMSimulator          pure, synchronous, no asyncio, no cache  -> unit-testable maths
SimulatorDataSource   asyncio adapter implementing MarketDataSource
```

Per tick, `GBMSimulator.step()`:

```python
z = np.random.standard_normal(n)                  # independent draws
if self._cholesky is not None:
    z = self._cholesky @ z                        # correlated: Z ~ N(0, C)
for i, ticker in enumerate(self._tickers):
    mu, sigma = self._params[ticker]["mu"], self._params[ticker]["sigma"]
    drift = (mu - 0.5 * sigma**2) * self._dt      # dt = 0.5 s / 5,896,800 s
    diffusion = sigma * math.sqrt(self._dt) * z[i]
    self._prices[ticker] *= math.exp(drift + diffusion)
    if random.random() < self._event_prob:        # 0.1 %: a 2–5 % shock
        self._prices[ticker] *= 1 + random.uniform(0.02, 0.05) * random.choice([-1, 1])
    result[ticker] = round(self._prices[ticker], 2)   # round output only
```

Key properties:

- Prices stay positive (multiplicative), are scale-free, and are kept at full precision internally.
- The Cholesky factor is rebuilt only on add/remove (O(n³), n < 50). The correlation structure is "0.3 market factor plus sector extras", which keeps the matrix positive-definite for any ticker mix.
- Unknown tickers (e.g. `PYPL` added by the LLM) get `uniform(50, 300)` as a seed and `DEFAULT_PARAMS`.
- At 10 tickers a step takes microseconds, so the adapter runs it inline on the event loop.

### 5.2 Adapter loop (built)

```python
async def _run_loop(self) -> None:
    while True:
        try:
            if self._sim:
                for ticker, price in self._sim.step().items():
                    self._cache.update(ticker=ticker, price=price)
        except Exception:
            logger.exception("Simulator step failed")   # never kill the loop
        await asyncio.sleep(self._interval)
```

### 5.3 Reference price (proposed, G1)

Pass the seed as the reference when a ticker first enters the cache. Every later `step()` update omits it, so it sticks.

```python
def _seed(self, ticker: str) -> None:
    price = self._sim.get_price(ticker) if self._sim else None
    if price is not None:
        self._cache.update(ticker=ticker, price=price, reference_price=price)

async def start(self, tickers: list[str]) -> None:
    self._sim = GBMSimulator(tickers=tickers, event_probability=self._event_prob)
    for ticker in tickers:
        self._seed(ticker)
    self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

async def add_ticker(self, ticker: str) -> None:
    if self._sim and ticker not in self._sim.get_tickers():
        self._sim.add_ticker(ticker)
        self._seed(ticker)
```

The `not in get_tickers()` guard matters now: re-adding an already-tracked ticker must not reset its reference to the current price.

---

## 6. Massive API client

Built in `massive_client.py`; endpoint and SDK details are in `MASSIVE_API.md`.

### 6.1 Modes

The client must work on every plan, including the free one, with **one API call per poll however many tickers are tracked**.

| Mode | SDK call | Plans | Default interval | Price meaning |
|---|---|---|---|---|
| `snapshot` | `get_snapshot_all(market_type="stocks", tickers=[...])` | Starter+ | 15 s | 15-min delayed (real-time on Advanced) |
| `eod` | `get_grouped_daily_aggs(date)` | All, incl. free | 900 s | Last trading day's close |

```
start() ──► snapshot poll ──ok──► stay in snapshot mode, poll every 15 s
                 │
                 └─ BadResponse containing NOT_AUTHORIZED (free key)
                        │
                        ▼
                 switch to eod permanently, warn once, interval 900 s, poll now
```

### 6.2 Pure helpers (built)

Kept as plain functions over real SDK models so they are trivial to test.

```python
def snapshot_price(snap: TickerSnapshot) -> PriceAndTime | None:
    """Best (price, unix_seconds) from a snapshot."""
    if snap.last_trade and snap.last_trade.price:              # Developer+
        return snap.last_trade.price, snap.last_trade.sip_timestamp / 1e9   # ns
    if snap.min and snap.min.close:                            # Starter: minute bar
        return snap.min.close, snap.min.timestamp / 1e3        # ms
    if snap.day and snap.day.close:                            # 0 before the open
        return snap.day.close, None
    if snap.prev_day and snap.prev_day.close:                  # pre-market
        return snap.prev_day.close, None
    return None


def latest_eod_closes(client: RESTClient, max_days_back: int = 5) -> dict[str, float]:
    """Closes for all US stocks from the latest trading day that has data.
    Starts at *New York* yesterday: free keys get 403 for the current market date."""
    day = datetime.now(MARKET_TZ).date() - timedelta(days=1)
    for _ in range(max_days_back):
        bars = client.get_grouped_daily_aggs(day.isoformat(), adjusted=True)
        if bars:
            return {b.ticker: b.close for b in bars if b.close}
        day -= timedelta(days=1)                               # weekend / holiday
    return {}
```

Two SDK traps the code already handles, and any new code must too:

- Pass `market_type="stocks"` as a **string**. `SnapshotMarketType.STOCKS` is a plain `Enum` and is formatted into the URL as `SnapshotMarketType.STOCKS`, which returns 404.
- `LastTrade` has no `timestamp`; use `sip_timestamp` (nanoseconds). `min.timestamp` is milliseconds.

### 6.3 Poll cycle (built)

```python
async def _poll_once(self) -> None:
    """One poll: fetch, write to cache. Never raises."""
    if not self._tickers or not self._client:
        return
    try:
        prices = await asyncio.to_thread(self._fetch)          # SDK is synchronous
    except BadResponse as e:
        if self._mode == "snapshot" and "NOT_AUTHORIZED" in str(e):
            logger.warning("Massive plan has no snapshot access; using end-of-day prices")
            self._mode, self._interval = "eod", self._eod_interval
            await self._poll_once()                            # eod can't recurse again
        else:
            logger.error("Massive poll failed: %s", e)
        return
    except Exception as e:                                     # network, timeouts
        logger.error("Massive poll failed: %s", e)
        return
    for ticker, (price, timestamp) in prices.items():
        self._cache.update(ticker=ticker, price=price, timestamp=timestamp)
```

The SDK already retries 429/5xx three times with backoff and times out after 10 s, so the poller adds no retry logic of its own; a failed poll simply waits for the next interval.

In EOD mode the grouped response holds **every** US stock, so the client keeps it in `self._eod_closes` and `add_ticker` prices a new ticker instantly without an API call.

### 6.4 Reference price (proposed, G1)

Return a small named tuple from `_fetch` instead of `(price, ts)`:

```python
class Quote(NamedTuple):
    price: float
    timestamp: float | None
    reference: float | None


def snapshot_reference(snap: TickerSnapshot) -> float | None:
    """Yesterday's close: the baseline Massive uses for todaysChangePerc."""
    return snap.prev_day.close if snap.prev_day and snap.prev_day.close else None


def latest_eod_bars(client: RESTClient, max_days_back: int = 5) -> dict[str, GroupedDailyAgg]:
    day = datetime.now(MARKET_TZ).date() - timedelta(days=1)
    for _ in range(max_days_back):
        bars = client.get_grouped_daily_aggs(day.isoformat(), adjusted=True)
        if bars:
            return {b.ticker: b for b in bars if b.close}
        day -= timedelta(days=1)
    return {}


def latest_eod_closes(client: RESTClient, max_days_back: int = 5) -> dict[str, float]:
    return {t: b.close for t, b in latest_eod_bars(client, max_days_back).items()}
```

`snapshot_price` and `latest_eod_closes` keep their signatures, so the existing tests stand. `self._eod_closes` becomes `self._eod_bars: dict[str, GroupedDailyAgg]`.

### 6.5 Fresh prices on add, and a thread-safe fetch (proposed, G5 and G6)

```python
async def add_ticker(self, ticker: str) -> None:
    ticker = ticker.upper().strip()
    if ticker in self._tickers:
        return
    self._tickers.append(ticker)
    if bar := self._eod_bars.get(ticker):                     # eod: no API call
        self._cache.update(ticker, bar.close, reference_price=bar.open or None)
    elif self._mode == "snapshot" and self._client:
        self._request_refresh()                               # price within ~1 s

def _request_refresh(self) -> None:
    """Coalesced out-of-band poll: several adds in a row cost one API call."""
    if self._refresh_task is None or self._refresh_task.done():
        self._refresh_task = asyncio.create_task(self._poll_once(), name="massive-refresh")

async def _poll_once(self) -> None:
    if not self._tickers or not self._client:
        return
    tickers = list(self._tickers)                             # G6: snapshot for the thread
    try:
        quotes = await asyncio.to_thread(self._fetch, tickers)
    except BadResponse as e:
        ...                                                   # unchanged
    for ticker, q in quotes.items():
        self._cache.update(ticker, q.price, timestamp=q.timestamp, reference_price=q.reference)

def _fetch(self, tickers: list[str]) -> dict[str, Quote]:
    if self._mode == "snapshot":
        snaps = self._client.get_snapshot_all(market_type="stocks", tickers=tickers)
        return {
            s.ticker: Quote(*p, snapshot_reference(s))
            for s in snaps if (p := snapshot_price(s))
        }
    self._eod_bars = latest_eod_bars(self._client)
    return {
        t: Quote(b.close, None, b.open or None)
        for t in tickers if (b := self._eod_bars.get(t))
    }
```

`stop()` also cancels `self._refresh_task`. A refresh already in flight when a second ticker is added does not include it; that ticker is priced on the next refresh or regular poll, which is acceptable.

The `sync_tracked_tickers()` helper (section 9) adds tickers one after another without awaiting the network, so adding five tickers through the LLM produces one refresh call, not five.

---

## 7. Factory and configuration

Built (`factory.py`):

```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    logger.info("Market data source: GBM Simulator")
    return SimulatorDataSource(price_cache=price_cache)
```

An unset, empty or whitespace-only key selects the simulator. The factory returns an **unstarted** source.

Tunables:

| Parameter | Where | Default | Notes |
|---|---|---|---|
| `MASSIVE_API_KEY` | env | empty | Selects the source |
| `update_interval` | `SimulatorDataSource` | 0.5 s | Tick length |
| `event_probability` | `SimulatorDataSource` / `GBMSimulator` | 0.001 | Shock chance per ticker per tick |
| `dt` | `GBMSimulator` | 0.5 / 5,896,800 | "Market speed" time step |
| `poll_interval` | `MassiveDataSource` | 15 s | Snapshot mode; 2–5 s is fine on Advanced |
| `eod_poll_interval` | `MassiveDataSource` | 900 s | EOD mode; free tier is 5 calls/min |
| SSE `interval` | `create_stream_router` | 0.5 s | Push cadence |
| SSE `keepalive` | `create_stream_router` | 15 s | Proposed, §8.3 |
| `retry:` | SSE preamble | 1000 ms | Browser reconnect delay |

Optional, if paid-tier users want faster polls (not in `PLAN.md` §5, so off by default):

```python
interval = float(os.environ.get("MASSIVE_POLL_INTERVAL", "15") or 15)
return MassiveDataSource(api_key=api_key, price_cache=price_cache, poll_interval=interval)
```

---

## 8. SSE stream

### 8.1 Wire format (built)

`GET /api/stream/prices`, `Content-Type: text/event-stream`, headers `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.

```
retry: 1000

data: {"AAPL": {"ticker": "AAPL", "price": 190.52, "previous_price": 190.48, "timestamp": 1760790000.5, "change": 0.04, "change_percent": 0.021, "direction": "up", "reference_price": 190.0, "day_change": 0.52, "day_change_percent": 0.2737}, "MSFT": {...}}

data: {...}

: ping
```

(`reference_price`, `day_change` and `day_change_percent` arrive with G1.)

Behaviour:

- Every `interval` the generator compares `cache.version` with the last version it sent and pushes the whole cache only if it changed. A new client starts with `last_version = -1`, so it gets the current prices at once, even on a free key where prices change once a day.
- `request.is_disconnected()` ends the generator; cancellation on shutdown is caught and logged.
- Polling the cache rather than being notified by the source gives evenly spaced events, which keeps sparklines clean.

### 8.2 Router created per call (proposed, G4)

```python
def create_stream_router(
    price_cache: PriceCache,
    interval: float = 0.5,
    keepalive: float = 15.0,
) -> APIRouter:
    router = APIRouter(prefix="/api/stream", tags=["streaming"])   # was module-level

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        return StreamingResponse(
            _generate_events(price_cache, request, interval, keepalive),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
```

Delete the module-level `router = APIRouter(...)`.

### 8.3 Keep-alive (proposed, G3)

SSE comment lines (starting with `:`) are ignored by `EventSource` but keep proxies and load balancers (App Runner, Render) from closing an idle stream.

```python
async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
    keepalive: float = 15.0,
) -> AsyncGenerator[str, None]:
    yield "retry: 1000\n\n"
    last_version = -1
    last_sent = time.monotonic()
    try:
        while not await request.is_disconnected():
            version = price_cache.version
            if version != last_version:
                last_version = version
                if prices := price_cache.get_all():
                    payload = json.dumps({t: u.to_dict() for t, u in prices.items()})
                    yield f"data: {payload}\n\n"
                    last_sent = time.monotonic()
            if time.monotonic() - last_sent >= keepalive:
                yield ": ping\n\n"
                last_sent = time.monotonic()
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled")
```

---

## 9. Tracked tickers: watchlist ∪ positions

### 9.1 Normalising and validating tickers (proposed, G7, `tracking.py`)

```python
import re

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")   # AAPL, BRK.B, RDS-A


def normalize_ticker(raw: str) -> str:
    """Upper-case and validate a symbol. Raises ValueError if it can't be a ticker."""
    ticker = raw.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise ValueError(f"Invalid ticker symbol: {raw!r}")
    return ticker
```

Every entry point calls it once: `POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`, `POST /api/portfolio/trade`, and each trade or watchlist change in the LLM's structured output. Routes turn the `ValueError` into a 400; the chat flow turns it into an error string reported back to the LLM.

Format validation is all the market layer does. On the simulator any well-formed symbol gets a price. On Massive a well-formed but unknown symbol simply never gets a price; trades on it fail with "no price available" (§12), which is clear enough for a demo.

### 9.2 Reconciliation (proposed, G2, `tracking.py`)

A held ticker removed from the watchlist must keep its price, or the portfolio cannot be valued. Rather than special-casing each route, every route that changes the watchlist or positions calls one idempotent helper with the full desired set:

```python
from collections.abc import Iterable

from .interface import MarketDataSource


async def sync_tracked_tickers(source: MarketDataSource, wanted: Iterable[str]) -> None:
    """Make the source track exactly `wanted` (already-normalised symbols)."""
    wanted_set = set(wanted)
    current = set(source.get_tickers())
    for ticker in sorted(wanted_set - current):
        await source.add_ticker(ticker)
    for ticker in sorted(current - wanted_set):
        await source.remove_ticker(ticker)
```

The backend supplies the desired set from SQLite (the DB layer is owned by the backend agent; the function names here are placeholders):

```python
def tracked_tickers(db) -> set[str]:
    return set(db.watchlist_tickers()) | set(db.held_tickers())   # quantity > 0

# after any watchlist change or trade, from REST or from chat:
await sync_tracked_tickers(source, tracked_tickers(db))
```

Flows:

```
POST /api/watchlist {ticker: "pypl"}
  normalize_ticker -> "PYPL"; insert row
  sync_tracked_tickers -> add_ticker("PYPL")
     simulator: seeded price in the cache now
     massive snapshot: coalesced refresh, price in ~1 s
     massive eod: priced from the cached grouped bars, no API call
  return {ticker, price: cache.get_price("PYPL")}       # price may be null on Massive

DELETE /api/watchlist/TSLA   (user still holds 5 TSLA)
  delete row; sync -> TSLA still wanted (held) -> stays tracked and priced

POST /api/portfolio/trade {ticker: "TSLA", side: "sell", quantity: 5}
  position goes to 0 and TSLA is not on the watchlist
  sync -> remove_ticker("TSLA") -> dropped from the cache
```

---

## 10. FastAPI integration

`app/main.py` (to be written by the backend agent). Market objects live on `app.state` and are injected with dependencies, so tests can build an app with a fake source.

```python
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request

from app.market import (
    MarketDataSource, PriceCache, create_market_data_source, create_stream_router,
)

price_cache = PriceCache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = init_db()                                     # lazy schema + seed (PLAN.md §7)
    source = create_market_data_source(price_cache)
    await source.start(sorted(tracked_tickers(db)))    # watchlist ∪ positions
    app.state.price_cache = price_cache
    app.state.market_source = source
    snapshot_task = asyncio.create_task(record_snapshots_every(30, db, price_cache))
    yield
    snapshot_task.cancel()
    await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(create_stream_router(price_cache))  # before the static mount


def get_cache(request: Request) -> PriceCache:
    return request.app.state.price_cache


def get_source(request: Request) -> MarketDataSource:
    return request.app.state.market_source
```

The stream router must be included **before** `app.mount("/", StaticFiles(...))`, or the static mount swallows `/api/stream/prices`.

Consumers:

```python
# Trade execution: fill at the cached price.
@router.post("/api/portfolio/trade")
async def trade(body: TradeIn, cache: PriceCache = Depends(get_cache),
                source: MarketDataSource = Depends(get_source)):
    ticker = normalize_ticker(body.ticker)
    price = cache.get_price(ticker)
    if price is None:
        raise HTTPException(400, f"No price available for {ticker} yet")
    result = execute_trade(db, ticker, body.side, body.quantity, price)   # validates cash/shares
    await sync_tracked_tickers(source, tracked_tickers(db))
    record_snapshot(db, cache)                                            # PLAN.md §7
    return result


# Watchlist with latest prices.
@router.get("/api/watchlist")
async def watchlist(cache: PriceCache = Depends(get_cache)):
    rows = []
    for ticker in db.watchlist_tickers():
        u = cache.get(ticker)
        rows.append({"ticker": ticker, **(u.to_dict() if u else {"price": None})})
    return rows


# Portfolio valuation (also used by snapshots and the LLM context).
def portfolio_value(db, cache: PriceCache) -> float:
    total = db.cash()
    for p in db.positions():
        price = cache.get_price(p.ticker) or p.avg_cost   # fall back rather than drop
        total += p.quantity * price
    return total
```

The LLM chat context (`PLAN.md` §9) reads the same cache: watchlist prices from `cache.get_all()` and position values from `portfolio_value()`. The chat handler applies trades and watchlist changes through the same functions as the REST routes, then calls `sync_tracked_tickers` once at the end.

`GET /api/health` can report the source cheaply:

```python
{"status": "ok", "market_data": {"source": type(source).__name__, "tickers": len(price_cache)}}
```

---

## 11. Frontend contract

What the frontend agent can rely on:

- Connect once with `new EventSource("/api/stream/prices")`. Reconnection is automatic (`retry: 1000`).
- Each `message` event's `data` is a JSON object keyed by ticker. Treat it as a **price feed**: merge it into a price map, but build the watchlist rows from `GET /api/watchlist` (the stream can include held tickers that are not on the watchlist, G8).
- A ticker that disappears from the payload has stopped being tracked.
- Flash on `direction` (`"up"`/`"down"`); `"flat"` means no flash.
- Show `day_change_percent` as the watchlist's daily change (G1).
- Sparklines: append `price` per event; on the simulator events arrive every ~500 ms, on Massive only when a poll changes something.
- Connection dot: `onopen` → green, `onerror` with `readyState === CONNECTING` → yellow, `CLOSED` → red. Comment lines (`: ping`) never fire `onmessage`.

```ts
type PriceUpdate = {
  ticker: string; price: number; previous_price: number; timestamp: number;
  change: number; change_percent: number; direction: "up" | "down" | "flat";
  reference_price: number | null; day_change: number; day_change_percent: number;
};

const es = new EventSource("/api/stream/prices");
es.onopen = () => setStatus("connected");
es.onerror = () =>
  setStatus(es.readyState === EventSource.CLOSED ? "disconnected" : "reconnecting");
es.onmessage = (e) => {
  const prices: Record<string, PriceUpdate> = JSON.parse(e.data);
  mergePrices(prices);   // update map, push sparkline points, trigger flashes
};
```

---

## 12. Error handling and edge cases

| Situation | Behaviour |
|---|---|
| Empty watchlist and no positions at startup | Both sources start with no tickers; simulator steps nothing, Massive skips its call; SSE sends nothing until a ticker is added (keep-alive pings continue) |
| Simulator `step()` raises | Logged with traceback; loop sleeps and continues |
| Massive network error / timeout / 5xx | SDK retries; then logged; next poll in one interval; cache keeps the last good prices |
| Free key (snapshot 403 `NOT_AUTHORIZED`) | One warning, permanent switch to EOD, immediate EOD poll |
| Invalid key (401) | Logged on every poll; no prices ever arrive; trades fail with 400. Fix the key and restart. (Optional polish: log the first failure at `error`, repeats at `debug`.) |
| Weekend / holiday on EOD | Grouped call returns empty; step back up to 5 days |
| Before the open on snapshot | `day.close == 0`; fall back to `prev_day.close` |
| Trade on a ticker with no cached price | 400 "No price available for X yet" |
| Unknown but well-formed symbol | Simulator invents a price; Massive never prices it (trade gets 400) |
| Malformed symbol | `normalize_ticker` raises → 400, or an error string in the chat response |
| Sell to zero on a ticker not on the watchlist | `sync_tracked_tickers` stops tracking it |
| Process restart | Simulator restarts from seed prices; positions are revalued at the new simulated price (known limitation) |
| Free-threaded Python (no GIL) | Cache is fully lock-guarded once `version` is read under the lock (§4.4) |

---

## 13. Testing

### 13.1 Existing coverage (`backend/tests/market/`, 84 tests)

| File | Covers |
|---|---|
| `test_models.py` | `PriceUpdate` properties, `to_dict`, immutability |
| `test_cache.py` | update/get/remove, first update flat, rounding, version counter |
| `test_simulator.py` | `step()`, seeds, unknown tickers, add/remove, Cholesky, correlation rules |
| `test_simulator_source.py` | start seeds the cache, updates flow, stop, add/remove, step exception survives |
| `test_factory.py` | key set / empty / whitespace selects the right source |
| `test_massive.py` | `snapshot_price` chain on real SDK models, EOD stepping back and NY date, poll → cache, `NOT_AUTHORIZED` fallback, snapshot URL, add/remove, stop |

Run with `cd backend && uv run --extra dev pytest -v`.

Rule from `MASSIVE_API.md` §5.3 that new tests must keep: build Massive fixtures from **real SDK models** (`TickerSnapshot.from_dict`, `GroupedDailyAgg.from_dict`), never `MagicMock` attributes, which hide field-name mistakes.

### 13.2 New tests for the proposed changes

```python
# test_cache.py — G1
def test_reference_price_defaults_to_first_price_and_sticks():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    u = cache.update("AAPL", 102.0)
    assert u.reference_price == 100.0
    assert u.day_change_percent == 2.0

def test_explicit_reference_price_overrides_and_sticks():
    cache = PriceCache()
    cache.update("AAPL", 100.0, reference_price=95.0)
    assert cache.update("AAPL", 101.0).reference_price == 95.0


# test_massive.py — G1 on a real snapshot
def test_snapshot_reference_is_prev_close():
    snap = TickerSnapshot.from_dict({"ticker": "AAPL", "prevDay": {"c": 188.0}})
    assert snapshot_reference(snap) == 188.0


# test_massive.py — G5: one refresh for several adds
async def test_add_ticker_coalesces_refresh():
    source, cache = _source(["AAPL"])
    source._client.get_snapshot_all.return_value = [
        _developer_snap("AAPL", 190.0), _developer_snap("MSFT", 420.0),
    ]
    await source.add_ticker("MSFT")
    await source.add_ticker("NVDA")
    await source._refresh_task
    assert source._client.get_snapshot_all.call_count == 1
    assert cache.get_price("MSFT") == 420.0


# test_stream.py (new) — G4 and G3, driving the generator with a fake request
class FakeRequest:
    client = None
    def __init__(self, polls: int):
        self._polls = polls
    async def is_disconnected(self) -> bool:
        self._polls -= 1
        return self._polls < 0

def test_router_factory_is_reentrant():
    r1, r2 = create_stream_router(PriceCache()), create_stream_router(PriceCache())
    assert [r.path for r in r1.routes] == ["/api/stream/prices"]
    assert [r.path for r in r2.routes] == ["/api/stream/prices"]

async def test_stream_sends_data_once_then_pings():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    events = [e async for e in _generate_events(cache, FakeRequest(3), interval=0, keepalive=0)]
    assert events[0] == "retry: 1000\n\n"
    assert events[1].startswith("data: ") and '"AAPL"' in events[1]
    assert sum(e.startswith("data: ") for e in events) == 1     # version unchanged after
    assert ": ping\n\n" in events


# test_tracking.py (new) — G2, G7
async def test_sync_adds_and_removes():
    cache = PriceCache()
    source = SimulatorDataSource(cache)
    await source.start(["AAPL", "TSLA"])
    await sync_tracked_tickers(source, {"AAPL", "PYPL"})
    assert set(source.get_tickers()) == {"AAPL", "PYPL"}
    assert "TSLA" not in cache and "PYPL" in cache
    await source.stop()

@pytest.mark.parametrize("raw,expected", [(" aapl ", "AAPL"), ("brk.b", "BRK.B")])
def test_normalize_ticker(raw, expected):
    assert normalize_ticker(raw) == expected

@pytest.mark.parametrize("raw", ["", "1ABC", "TOOLONGSYMBOL", "AA PL", "$AAPL"])
def test_normalize_ticker_rejects(raw):
    with pytest.raises(ValueError):
        normalize_ticker(raw)
```

### 13.3 Statistical checks for the simulator (recommended in `MARKET_SIMULATOR.md` §9)

```python
def test_log_returns_match_gbm_parameters():
    np.random.seed(0); random.seed(0)
    sim = GBMSimulator(["AAPL"], dt=1 / 252, event_probability=0)   # daily steps
    prices = [sim.get_price("AAPL")]
    for _ in range(20_000):
        sim.step()
        prices.append(sim.get_price("AAPL"))                        # full precision
    r = np.diff(np.log(prices))
    sigma, mu = 0.22, 0.05
    assert abs(r.std() - sigma * math.sqrt(1 / 252)) < 0.002
    assert abs(r.mean() - (mu - sigma**2 / 2) / 252) < 0.0005

def test_tech_pair_correlation_is_about_point_six():
    np.random.seed(1); random.seed(1)
    sim = GBMSimulator(["AAPL", "MSFT", "JPM"], dt=1 / 252, event_probability=0)
    rows = []
    for _ in range(5_000):
        before = [sim.get_price(t) for t in ("AAPL", "MSFT", "JPM")]
        sim.step()
        rows.append([math.log(sim.get_price(t) / b) for t, b in zip(("AAPL", "MSFT", "JPM"), before)])
    c = np.corrcoef(np.array(rows).T)
    assert abs(c[0, 1] - 0.6) < 0.05      # tech-tech
    assert abs(c[0, 2] - 0.3) < 0.05      # cross-sector
```

These use `get_price()` (full precision) rather than `step()`'s rounded output, and a daily `dt` so the moves are well above the rounding floor.

---

## 14. Implementation checklist

Proposed changes, in a sensible order. Each is small and independently testable; none changes the public API in a breaking way.

| # | Change | Files | Gap |
|---|---|---|---|
| 1 | Router created inside `create_stream_router`; add keep-alive | `stream.py`, new `tests/market/test_stream.py` | G4, G3 |
| 2 | `reference_price` on `PriceUpdate` and `PriceCache.update`; `version` under lock | `models.py`, `cache.py`, tests | G1 |
| 3 | Simulator seeds the reference; guard re-add | `simulator.py`, tests | G1 |
| 4 | Massive `Quote`, `snapshot_reference`, `latest_eod_bars`; copy tickers into the thread; coalesced refresh on add | `massive_client.py`, tests | G1, G5, G6 |
| 5 | `normalize_ticker` and `sync_tracked_tickers`; export from `__init__` | new `tracking.py`, new `tests/market/test_tracking.py` | G2, G7 |
| 6 | Update `MARKET_INTERFACE.md` and `backend/CLAUDE.md` with the new payload fields and helpers | docs | — |

Then the backend agent wires section 10 into `app/main.py` alongside the database, portfolio, watchlist and chat routes, and the frontend agent consumes section 11.
