# Phase 5: Real Market Data (Massive) - Pattern Map

**Mapped:** 2026-10-20
**Files analyzed:** 15 (6 new, 9 modified)
**Analogs found:** 14 / 15

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/market/massive_source.py` (new) | service (background source) | polling / event-driven | `backend/app/market/simulator_source.py` | exact |
| `backend/app/market/massive_parse.py` (new) | utility (pure parsing) | transform | `backend/app/market/simulator.py` (pure, sync engine) + `models.py` | role-match |
| `backend/app/market/factory.py` (modify) | config / factory | request-response (env read) | itself + `backend/app/main.py:25` (env read style) | exact |
| `backend/app/market/cache.py` (modify) | store | CRUD (in-memory) | itself | exact |
| `backend/app/market/simulator_source.py` (modify: `name = "simulator"`) | service | polling | itself | exact |
| `backend/app/market/__init__.py` (modify) | config (barrel) | - | itself | exact |
| `backend/app/api/health.py` (modify) | route | request-response | `backend/app/api/watchlist.py` (`create_*_router(cache, source)`) | role-match |
| `backend/app/main.py` (modify: health router wiring) | config / app | - | itself lines 69-73 | exact |
| `backend/tests/conftest.py` (modify: blank key) | test fixture | - | itself (`no_network` guard) | exact |
| `backend/tests/market/test_massive_source.py` (new) | test | async polling | `backend/tests/market/test_source.py` | exact |
| `backend/tests/market/test_massive_parse.py` (new) | test | transform | `backend/tests/market/test_cache.py` / `test_simulator.py` | role-match |
| `backend/tests/market/test_factory.py` (new) | test | env selection | `backend/tests/market/test_interface.py` | exact |
| `backend/tests/market/test_cache.py` (extend) | test | CRUD | itself | exact |
| `backend/tests/test_health.py` (modify) | test | request-response | itself | exact |
| `frontend/src/lib/usePriceStream.ts` (modify: `asOf`) | hook | streaming (SSE) | itself | exact |
| `frontend/src/components/Header.tsx` (modify: badge) | component | render | itself + `ConnectionStatus.tsx` | exact |
| `frontend/src/components/Terminal.tsx` (modify: pass `asOf`) | component | render | itself line 19, 35 | exact |
| `backend/pyproject.toml` / `uv.lock` | config | - | `uv add massive` only (never hand-edit) | n/a |

No analog: Massive SDK fake client (no existing SDK fake in repo; closest is `llm_reply` fixture in `conftest.py` lines 65-88, use RESEARCH.md "Fake client for tests").

## Pattern Assignments

### `backend/app/market/massive_source.py` (service, polling)

**Analog:** `backend/app/market/simulator_source.py` (60 lines) - copy structure verbatim, swap simulator for client.

**Imports + logger** (lines 1-11):
```python
"""Background task that feeds simulated prices into the cache."""

import asyncio
import contextlib
import logging

from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.market.simulator import GBMSimulator

logger = logging.getLogger(__name__)
```
Add `from datetime import datetime` and `from app.market.massive_parse import NY, latest_grouped_bars, not_authorized, snapshot_quote, ...`. Import `BadResponse` from `massive.exceptions`.

**Constructor** (lines 14-24) - injected deps, `_task: asyncio.Task | None = None`:
```python
class SimulatorDataSource(MarketDataSource):
    """Runs GBMSimulator on an interval and writes each step to the cache."""

    def __init__(
        self, cache: PriceCache, update_interval: float = 0.5, event_probability: float = 0.001
    ) -> None:
        self._cache = cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None
```
Massive version: `__init__(self, cache, client, interval=15.0)`; fields `_mode = "snapshot"`, `_tickers: list[str]`, `_bars: dict`, `_task`. Class attr `name = "massive"`.

**start: seed cache before returning, then create named task** (lines 26-31):
```python
    async def start(self, tickers: list[str]) -> None:
        """Seed the cache, then start the update loop."""
        self._sim = GBMSimulator(tickers, event_probability=self._event_prob)
        for t in tickers:
            self._cache.update(t, self._sim.get_price(t))
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
```
Massive: `self._tickers = list(tickers)`, `await self._poll_once()` (wrapped so a startup failure is logged, not raised), then `create_task(self._run_loop(), name="massive-loop")`. Seeding before return matters: `main.py` line 50 records a snapshot right after `source.start`.

**stop (idempotent)** (lines 33-38) - copy unchanged:
```python
    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
```

**add/remove with early return for tracked tickers** (lines 40-51):
```python
    async def add_ticker(self, ticker: str) -> None:
        if ticker in self._sim.tickers:
            return
        self._sim.add_ticker(ticker)
        self._cache.update(ticker, self._sim.get_price(ticker))

    async def remove_ticker(self, ticker: str) -> None:
        self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.tickers if self._sim else []
```
Massive `add_ticker`: early return if tracked (critical, `services.reconcile_stream` calls it after every trade), append, then one fetch via `asyncio.to_thread` (snapshot: `get_snapshot_ticker("stocks", t)`; EOD: `self._bars.get(t)` else `get_previous_close_agg(t)`); on exception `logger.exception(...)` and leave no cache entry. `remove_ticker`: drop from `_tickers` if present, `self._cache.remove(ticker)`. `get_tickers`: `list(self._tickers)`.

**Loop with log-and-continue** (lines 53-60):
```python
    async def _run_loop(self) -> None:
        while True:
            try:
                for ticker, price in self._sim.step().items():
                    self._cache.update(ticker, price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```
Massive: `await asyncio.sleep(self._interval)` first (start already polled), then `try: await self._poll_once() except Exception: logger.exception("Massive poll failed")`. Snapshot->EOD switch happens once inside `_poll_once` only when `self._mode == "snapshot"` (RESEARCH Pitfall 4); set `self._interval = max(self._interval, 900)` on switch. Every `cache.update` call passes `timestamp=` and `reference=` explicitly; never `None` timestamp.

---

### `backend/app/market/massive_parse.py` (utility, transform)

**Analog:** `backend/app/market/simulator.py` - pure, synchronous module, module docstring, private helpers with one-line docstrings.

**Module/helper style** (lines 1, 20-28):
```python
"""Correlated geometric Brownian motion price engine (pure, synchronous)."""
...
def _pair_correlation(a: str, b: str) -> float:
    """Correlation between two distinct tickers from the sector rules."""
    if "TSLA" in (a, b):
        return TSLA_CORR
    ...
```
Contents come from RESEARCH.md Patterns 1 and 2 and the `not_authorized` helper: `NY = ZoneInfo("America/New_York")`, `Quote = tuple[float, float, float | None]`, `snapshot_quote(snap)`, `bar_quote(bar)` -> `(bar.close, bar.timestamp / 1e3, bar.open)`, `latest_grouped_bars(client, today, tries=5)`, `not_authorized(e)`. Constants module-level like `seed_prices.py` (e.g. `EOD_MIN_INTERVAL = 900`). No I/O beyond the client call passed in; caller wraps with `asyncio.to_thread`.

---

### `backend/app/market/factory.py` (factory)

**Analog:** itself (lines 1-10) - keep the docstring/import shape:
```python
"""Selects the market data source for the app."""

from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.market.simulator_source import SimulatorDataSource


def create_market_data_source(cache: PriceCache) -> MarketDataSource:
    """Return the simulator (Massive selection arrives in Phase 5)."""
    return SimulatorDataSource(cache)
```
Env-read style from `backend/app/main.py` line 25: `os.environ.get("STATIC_DIR", ...)`. Body per RESEARCH "Factory" example: `key = os.environ.get("MASSIVE_API_KEY", "").strip()`; interval `float(os.environ.get("MASSIVE_POLL_INTERVAL", "").strip() or 15)`; `MassiveDataSource(cache, RESTClient(api_key=key), interval)`. Note `factory.py` runs at import of `app.main` (line 28 `source = create_market_data_source(cache)`), after `load_dotenv` (line 15).

---

### `backend/app/market/cache.py` (store, modify `update`)

**Analog:** itself, lines 18-33:
```python
    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Store a new price; the first price seen becomes the session open."""
        price = round(price, 2)
        with self._lock:
            prev = self._prices.get(ticker)
            open_price = self._opens.setdefault(ticker, price)
            update = PriceUpdate(
                ticker=ticker,
                price=price,
                previous_price=prev.price if prev else price,
                timestamp=timestamp if timestamp is not None else time.time(),
                session_open=open_price,
            )
```
Change: add `reference: float | None = None`; before `setdefault`, `if reference is not None: self._opens[ticker] = round(reference, 2)` (RESEARCH Pattern 4). Update docstring. `remove` (lines 43-47) already pops `_opens`; no change. `PriceUpdate.day_change_pct` (`models.py` lines 25-27) uses `session_open` and needs no change.

---

### `backend/app/market/simulator_source.py` + `__init__.py` (small modify)

- Add class attr `name = "simulator"` under the class docstring (line 15) so health can read `source.name`.
- `__init__.py` lines 3-19: add `from app.market.massive_source import MassiveDataSource` and `"MassiveDataSource"` to the sorted `__all__`. Keep import order alphabetical by module.

---

### `backend/app/api/health.py` (route, request-response)

**Current** (lines 1-10):
```python
"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
```
**Analog for injecting the source:** `backend/app/api/watchlist.py` lines 1-19:
```python
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
...
def create_watchlist_router(cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter()
```
Convert to `create_health_router(source: MarketDataSource) -> APIRouter` returning `{"status": "ok", "source": source.name}`. Add `name: str` as a plain class attribute on `MarketDataSource` (`interface.py` line 6) or rely on both subclasses defining it.

### `backend/app/main.py` (wiring)

Lines 18 and 69-73 - follow the factory-router pattern already used:
```python
from app.api.health import router as health_router
...
app.include_router(health_router)
app.include_router(create_stream_router(cache))
app.include_router(create_watchlist_router(cache, source))
```
Change to `from app.api.health import create_health_router` and `app.include_router(create_health_router(source))`. Lifespan (lines 43-56) needs no change: `await source.start(tickers)` then snapshot; `await source.stop()` at shutdown. Docstring line 1 says "simulator lifespan"; update to "market data lifespan".

---

### `backend/tests/conftest.py` (fixture, modify)

**Current top** (lines 1-4):
```python
import httpx
import pytest

from app import main
```
Insert `import os` and `os.environ["MASSIVE_API_KEY"] = ""` before `from app import main` (RESEARCH Pitfall 1; `load_dotenv` does not override existing env). Guard style to mirror if adding a network guard for Massive: `no_network` autouse fixture lines 51-62 (`pytest.fail("network call in test")`).

---

### `backend/tests/market/test_massive_source.py` (test, async polling)

**Analog:** `backend/tests/market/test_source.py`.

**Running-source fixture** (lines 11-18):
```python
@pytest.fixture
async def running():
    """A started source with a fast interval; always stopped afterwards."""
    cache = PriceCache()
    source = SimulatorDataSource(cache, update_interval=0.02)
    await source.start(DEFAULT_TICKERS)
    yield cache, source
    await source.stop()
```
**Add/remove assertions** (lines 35-42):
```python
async def test_add_and_remove_ticker(running):
    cache, source = running
    await source.add_ticker("PYPL")
    assert "PYPL" in source.get_tickers()
    assert cache.get("PYPL") is not None
    await source.remove_ticker("PYPL")
    assert "PYPL" not in source.get_tickers()
    assert cache.get("PYPL") is None
```
**Loop-survives-exception with caplog** (lines 54-73):
```python
    with caplog.at_level(logging.ERROR):
        await asyncio.sleep(0.15)
    await source.stop()
    assert cache.version > version
    assert "Simulator step failed" in caplog.text
```
Use `MassiveDataSource(cache, FakeClient(...), interval=0.02)`; FakeClient from RESEARCH "Fake client for tests" (records `calls`, raises stored exceptions). Build SDK models with `TickerSnapshot.from_dict` / `GroupedDailyAgg.from_dict`. Test names should contain the `-k` keywords in VALIDATION: `fallback`, `eod`, `survives`, `timestamp`, `add_ticker`. pytest-asyncio is in auto mode (`pyproject.toml` line 21), so plain `async def test_...` works, no decorators.

### `backend/tests/market/test_massive_parse.py` (test, transform)

**Analog:** `backend/tests/market/test_cache.py` - sync tests, one-line docstrings, direct asserts (lines 6-11):
```python
def test_first_update_is_flat():
    """First update has no previous price and no change."""
    u = PriceCache().update("AAPL", 190.0)
    assert u.direction == "flat"
```
Names carry `quote` and `grouped` for the `-k` filters. `latest_grouped_bars` tests pass a fixed `date(...)` and a FakeClient with `grouped={"2026-10-19": [...]}`; no clock patching.

### `backend/tests/market/test_factory.py` (test, env selection)

**Analog:** `backend/tests/market/test_interface.py` lines 1-19:
```python
from app.market import MarketDataSource, PriceCache, SimulatorDataSource, create_market_data_source
...
def test_factory_returns_simulator():
    """The factory defaults to the simulator."""
    assert isinstance(create_market_data_source(PriceCache()), SimulatorDataSource)
```
Use `monkeypatch.setenv("MASSIVE_API_KEY", "test-key")` / `"  "` / `delenv`, as `conftest.py` line 11 does with `DB_PATH`. `RESTClient(api_key="x")` makes no network call at construction (RESEARCH), so asserting `isinstance(..., MassiveDataSource)` is offline-safe. Existing `test_factory_returns_simulator` keeps passing because conftest blanks the key.

### `backend/tests/market/test_cache.py` (extend)

Add `reference` tests in the same style as `test_day_change_against_session_open` (lines 24-29):
```python
def test_day_change_against_session_open():
    """Day change is measured from the first price seen."""
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    assert cache.update("AAPL", 101.5).day_change_pct == 1.5
```
Plus a timestamp-preserved test: `cache.update("AAPL", 1.0, timestamp=123.0).timestamp == 123.0`.

### `backend/tests/test_health.py` (modify)

Lines 6-12; change docstring and assertion to `{"status": "ok", "source": "simulator"}`. Note it imports `app.main` directly (line 3), so it relies on conftest blanking the key before that import (conftest loads first).

---

### `frontend/src/lib/usePriceStream.ts` (hook, SSE)

**Analog:** itself. State declarations (lines 42-47) and `onmessage` (lines 57-70):
```ts
  const [status, setStatus] = useState<Status>("reconnecting");
  ...
    es.onmessage = (e) => {
      const next: Record<string, Quote> = JSON.parse(e.data);
      setQuotes((prev) => withRenderedDirection(prev, next));
```
Add `const [asOf, setAsOf] = useState<number | null>(null);` and, inside `onmessage`, compute staleness there (not in render; `react-hooks/purity` flags `Date.now()` in render). Every event carries the full cache (`backend/app/api/stream.py` line 20: `payload = {t: u.to_dict() for t, u in cache.get_all().items()}`), so the newest timestamp of `next` is the newest overall; guard the empty-object case before `Math.max`. Return `asOf` in the hook result (line 74). Keep helpers as top-level `function` with `/** ... */` docstrings like `appendPoint` (lines 20-27).

### `frontend/src/components/Header.tsx` (component)

**Analog:** itself (lines 5-29) and `ConnectionStatus.tsx` for muted small text.
```tsx
type Props = { status: Status; hasConnected: boolean; total?: number; cash?: number };
...
      <div className="ml-auto">
        <ConnectionStatus status={status} hasConnected={hasConnected} />
      </div>
```
Muted label class from `ConnectionStatus.tsx` line 32: `className="text-xs font-semibold text-text-muted"`. Add `asOf?: number | null` to Props; render `{asOf != null && <span data-testid="stale-badge" className="text-xs text-text-muted">EOD · as of {date}</span>}` next to `ConnectionStatus` inside the `ml-auto` div (make it `flex items-center gap-3`). Date via `new Date(asOf * 1000).toLocaleDateString("en-US", { timeZone: "America/New_York", ... })` (Pitfall 6). No new colours.

### `frontend/src/components/Terminal.tsx` (wiring)

Line 19 destructure and line 35 prop pass:
```tsx
  const { status, hasConnected, quotes, history, chart } = usePriceStream();
  ...
      <Header status={status} hasConnected={hasConnected} total={total} cash={portfolio?.cash_balance} />
```
Add `asOf` to both.

## Shared Patterns

### Sync I/O off the event loop
**Source:** `backend/app/main.py` lines 46-50; `backend/app/services.py` line 33
```python
    await asyncio.to_thread(db.init_db)
    tickers = await asyncio.to_thread(streaming.streamed_tickers)
```
**Apply to:** every Massive SDK call in `massive_source.py` (`await asyncio.to_thread(self._client.get_snapshot_all, "stocks", tickers=self._tickers)`).

### Log-and-continue error handling
**Source:** `simulator_source.py` lines 58-59, `services.py` lines 36-39
```python
    except Exception:
        logger.exception("post-trade snapshot failed")
```
**Apply to:** poll loop, startup poll, `add_ticker` fetch. Use module `logger = logging.getLogger(__name__)`. Never log the client or env (key safety); `str(BadResponse)` is the response body and is safe.

### Callers of `add_ticker` (hold trade lock)
**Source:** `backend/app/services.py` lines 23-50
```python
            if cache.get(ticker) is None:
                await source.add_ticker(ticker)
            update = cache.get(ticker)
            if update is None:
                raise portfolio.TradeError(f"No price available for {ticker}")
```
**Apply to:** `MassiveDataSource.add_ticker` must populate the cache before returning (or leave it empty so this raises 400). `add_to_watchlist` calls it only when `created`. `reconcile_stream` calls it after every trade, hence the tracked-ticker early return.

### Docstring / module style
One-line module docstring on every file; one-line method docstrings; short functions; no emojis. Seen across all `backend/app/market/*.py`.

### Test style
Plain functions, one-line docstrings, `async def` tests with no markers (asyncio auto mode), fixtures with `yield` + cleanup, `monkeypatch.setenv` for env, `caplog.at_level(logging.ERROR)` for log assertions.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| FakeClient (inside `test_massive_source.py` or conftest) | test double | - | No SDK fakes exist; nearest is `llm_reply` fixture (`conftest.py` 65-88, call recording via `calls` list). Use RESEARCH.md "Fake client for tests". |

Reference only (not an analog to copy): prior build `git show f2ef207^:backend/app/market/massive_client.py` - has known timestamp/add_ticker/day-change defects.

## Metadata

**Analog search scope:** `backend/app/market/`, `backend/app/api/`, `backend/app/main.py`, `backend/app/services.py`, `backend/tests/`, `frontend/src/components/`, `frontend/src/lib/`
**Files scanned:** 24
**Pattern extraction date:** 2026-10-20
