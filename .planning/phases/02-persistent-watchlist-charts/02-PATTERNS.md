# Phase 2: Persistent Watchlist & Charts - Pattern Map

**Mapped:** 2026-10-19
**Files analyzed:** 17 (new/modified)
**Analogs found:** 14 / 17 (3 have no codebase analog; use RESEARCH.md)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/db/schema.sql` | config (DDL) | batch | none (RESEARCH.md "schema.sql") | no analog |
| `backend/app/db.py` | service (repository) | CRUD | none in repo; RESEARCH.md Pattern 1; module style from `app/market/cache.py` | no analog |
| `backend/app/api/watchlist.py` | route (router factory) | request-response CRUD | `backend/app/api/stream.py` | role-match (factory) |
| `backend/app/main.py` (modify) | config/lifespan | event-driven | itself (lines 33-45) | exact |
| `backend/tests/conftest.py` (new) | test fixture | request-response | `backend/tests/market/test_stream.py` fixture + `tests/test_health.py` | partial |
| `backend/tests/test_db.py` | test | CRUD | `backend/tests/market/test_cache.py` | role-match |
| `backend/tests/test_watchlist_api.py` | test | request-response | `backend/tests/test_health.py` | role-match |
| `.gitignore` (modify) | config | n/a | existing `db/*.db` line | exact |
| `frontend/src/lib/useWatchlist.ts` | hook | request-response CRUD | `frontend/src/lib/usePriceStream.ts` | role-match |
| `frontend/src/lib/usePriceStream.ts` (modify) | hook | streaming | itself | exact |
| `frontend/src/lib/tickers.ts` (delete) | utility | n/a | n/a | n/a |
| `frontend/src/components/MainChart.tsx` | component | streaming | `frontend/src/components/Sparkline.tsx` (props) + `Panel.tsx` | partial |
| `frontend/src/components/WatchlistAddForm.tsx` | component | request-response | none (no form exists); tokens from `WatchlistRow.tsx` | no analog |
| `frontend/src/components/Watchlist.tsx` (modify) | component | transform | itself | exact |
| `frontend/src/components/WatchlistRow.tsx` (modify) | component | event-driven | itself | exact |
| `frontend/src/components/Terminal.tsx` (modify) | component | composition | itself | exact |
| `frontend/src/components/Panel.tsx` (modify) | component | n/a | itself | exact |

## Pattern Assignments

### `backend/app/api/watchlist.py` (route, request-response)

**Analog:** `backend/app/api/stream.py` (router factory taking dependencies) and `health.py` (docstring + `@router` style).

**Imports/docstring/factory pattern** (stream.py lines 1-12, 36-44 in file):
```python
"""SSE price stream."""

import asyncio
from fastapi import APIRouter
from app.market.cache import PriceCache

def create_stream_router(cache: PriceCache, interval: float = 0.5) -> APIRouter:
    router = APIRouter()

    @router.get("/api/stream/prices", response_class=EventSourceResponse)
    async def stream_prices() -> AsyncIterable[ServerSentEvent]:
        ...
    return router
```
Apply: `create_watchlist_router(cache: PriceCache, source: MarketDataSource) -> APIRouter`; full paths in decorators (`/api/watchlist`), no router prefix, as in health.py/stream.py. Single-line module docstring, short functions.

**Core pattern** (from RESEARCH.md Pattern 3; no repo analog for pydantic body/to_thread):
```python
class AddTicker(BaseModel):
    ticker: str
    @field_validator("ticker", mode="before")
    @classmethod
    def normalize(cls, v):
        v = str(v).strip().upper()
        if not re.fullmatch(r"[A-Z]{1,5}", v):
            raise ValueError("ticker must be 1-5 letters")
        return v

@router.post("/api/watchlist", status_code=201)
async def add(body: AddTicker, response: Response):
    row, created = await asyncio.to_thread(db.add_ticker, db.db_path(), body.ticker)
    if created:
        await source.add_ticker(body.ticker)
    else:
        response.status_code = 200
    return item(row)

@router.delete("/api/watchlist/{ticker}", status_code=204)
async def remove(ticker: str):
    t = ticker.strip().upper()
    if not await asyncio.to_thread(db.remove_ticker, db.db_path(), t):
        raise HTTPException(404, "Ticker not on watchlist")
    await source.remove_ticker(t)
```
GET item builder: `u = cache.get(t)`; price fields from `u.price/previous_price/direction/day_change_pct`, null when `u is None`. Use `PriceUpdate` fields from `app/market/models.py` (check names there; `to_dict()` has six keys: ticker, price, previous_price, timestamp, direction, day_change_pct). Interface used: `MarketDataSource.add_ticker/remove_ticker` (interface.py lines 18-23), both async.

---

### `backend/app/main.py` (modify: lifespan + router wiring)

**Analog:** itself. Current code (lines 11-13, 33-43 in the file dump):
```python
from app.api.health import router as health_router
from app.api.stream import create_stream_router, shutdown
from app.market import DEFAULT_TICKERS, PriceCache, create_market_data_source

@asynccontextmanager
async def lifespan(app: FastAPI):
    end_streams_on_exit_signal()
    await source.start(DEFAULT_TICKERS)
    yield
    await source.stop()

app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(health_router)
app.include_router(create_stream_router(cache))
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(...), name="static")   # MUST stay last
```
Change: drop `DEFAULT_TICKERS` import from main (move to `db.py` for seeding), replace `source.start(DEFAULT_TICKERS)` with `await asyncio.to_thread(db.init_db)`, `tickers = await asyncio.to_thread(db.list_tickers)`, `await source.start(tickers)`. Add `app.include_router(create_watchlist_router(cache, source))` before the static mount. Keep module-level `cache` and `source` (tests clear the cache; RESEARCH Pitfall 4).

---

### `backend/app/db.py` (service, CRUD) - no repo analog

Use RESEARCH.md Pattern 1 and "init_db + seed" verbatim: connection-per-call, `with closing(connect(path)) as conn, conn:`, `row_factory = sqlite3.Row`, `db_path()` reads `os.environ.get("DB_PATH", ...)` at call time, default `Path(__file__).parents[2] / "db" / "finally.db"`, schema at `Path(__file__).parents[1] / "db" / "schema.sql"`. `PRAGMA journal_mode=WAL` before `executescript`. Seed only when `users_profile` empty. `list_tickers` uses `ORDER BY rowid`. Parameterized `?` queries only. Style conventions to copy from `app/market/*.py`: one-line docstring per function, short functions, `DEFAULT_TICKERS` from `app.market.seed_prices`.

### `backend/db/schema.sql` - no analog
Copy RESEARCH.md "schema.sql (DATA-02)". All `CREATE TABLE IF NOT EXISTS`. Flag A2 (users_profile has `id` not `user_id`).

---

### `backend/tests/conftest.py`, `test_db.py`, `test_watchlist_api.py` (tests)

**Analogs:** `backend/tests/test_health.py` (ASGITransport client), `backend/tests/market/test_stream.py` (fixture style, no class wrappers, docstring per test).

**Client pattern** (test_health.py lines 1-12):
```python
import httpx
from app.main import app

async def test_health_returns_ok():
    """Health endpoint returns exactly {"status": "ok"}."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
```
**Fixture style** (test_stream.py lines 11-17): plain `@pytest.fixture` functions, async tests with no marker (pytest-asyncio auto mode; `pyproject.toml` has `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `pythonpath = ["."]`).

Extend with the lifespan fixture from RESEARCH.md "Pytest fixture" (monkeypatch `DB_PATH` to `tmp_path`, clear `main.cache`, `async with app.router.lifespan_context(app)`). Put it in `backend/tests/conftest.py` (none exists yet; `tests/market/` has no conftest either). Keep `test_health.py` unchanged (no lifespan needed). Note lifespan chaining of signal handlers is harmless. Docstring first line per test, no emojis.

---

### `frontend/src/lib/useWatchlist.ts` (hook, CRUD)

**Analog:** `frontend/src/lib/usePriceStream.ts`

**Conventions** (lines 1-13, 29-35):
```ts
"use client";

import { useEffect, useState } from "react";

export type Quote = { ... };

export function usePriceStream() {
  const [status, setStatus] = useState<Status>("reconnecting");
  ...
  useEffect(() => { ...; return () => es.close(); }, []);
  return { status, hasConnected, quotes, history };
}
```
Apply: `"use client"`, named hook export, exported row type, returns object `{rows, loading, error, add, remove}`; same-origin `fetch("/api/watchlist")`; no `.env`/base URL. `add` POSTs then `await load()`; `remove` treats 204 and 404 as removed then `load()`. No defensive over-engineering; 422 detail surfaces as inline error.

---

### `frontend/src/lib/usePriceStream.ts` (modify: 1000-point chart buffer)

**Analog:** itself (lines 15, 43-51):
```ts
const MAX_POINTS = 120;
...
es.onmessage = (e) => {
  const next: Record<string, Quote> = JSON.parse(e.data);
  setQuotes((prev) => withRenderedDirection(prev, next));
  setHistory((prev) =>
    Object.fromEntries(
      Object.entries(next).map(([t, q]) => [t, [...(prev[t] ?? []), q.price].slice(-MAX_POINTS)]),
    ),
  );
};
```
Add a third `setChart` with the same `Object.fromEntries(Object.entries(next).map(...))` shape (this automatically prunes removed tickers), `CHART_POINTS = 1000`, and the floor-to-second dedupe from RESEARCH Pattern 5 (skip older, replace equal, append else; `.slice(-CHART_POINTS)`). Return `chart` alongside `history`. Keep the 120-pt sparkline buffer untouched.

---

### `frontend/src/components/MainChart.tsx` (component, streaming)

**Analog:** `Sparkline.tsx` (props-only, typed inline, `export default function`, tokens via `var(--color-up)` CSS vars) and `Panel.tsx` (host).

Excerpt - style tokens (Sparkline line 17-18 of that file): `stroke={up ? "var(--color-up)" : "var(--color-down)"}`. Note that LWC takes literal colors, not CSS vars; use `#209dd7` line and `rgba(32,157,215,0.28)` top (RESEARCH Pattern 4; check UI-SPEC for bg/grid token values, read via `getComputedStyle` only if needed).

Core: RESEARCH.md Pattern 4 (`"use client"`; create-once effect with `chart.remove()` cleanup; `chart.addSeries(AreaSeries, ...)`; `[ticker]` effect does `setData` + `fitContent()`; per-tick effect does `series.update(last)` guarded by last-applied-time ref; chart container stays mounted under `main-chart-empty` overlay; `autoSize: true`; wrapper `relative h-full`).

Panel host: Panel's body is `min-h-0 flex-1 overflow-auto` (Panel.tsx line "div className"); chart needs a non-scrolling, sized wrapper (Pitfall 2) - either add a prop to Panel (e.g. `bodyClassName`) or wrap with `h-full`.

---

### `frontend/src/components/WatchlistAddForm.tsx` (component) - no analog

No form/input exists. Use class vocabulary from existing components: `border-border`, `bg-surface`, `text-text-muted`, `text-xs`, `font-mono`, `px-2`; purple button `#753991` per PLAN.md/UI-SPEC; test ids `watchlist-add-input`, `watchlist-add-button`. Follow `02-UI-SPEC.md` for pending/error contract. Enter submits via `<form onSubmit>`.

---

### `frontend/src/components/Watchlist.tsx` (modify)

**Analog:** itself. Replace `import { DEFAULT_TICKERS } from "@/lib/tickers"` and `DEFAULT_TICKERS.map((t) => ...)` (lines 1, 111-121 of dump) with `rows.map((r) => <WatchlistRow key={r.ticker} ticker={r.ticker} .../>)`; add `rows`, `onRemove`, `onAdd`, error props. Existing `Notice` (lines 68-84) fix ordering: Reconnecting before Waiting for prices, and not for an empty list; wrap in fixed-height slot (e.g. `min-h-[..]`) to prevent layout shift. Header row (lines 102-110) gets `role="columnheader"` on spans; wrap rows so table roles are valid (`role="table"` > `role="rowgroup"`/`row` > `cell`).

### `frontend/src/components/WatchlistRow.tsx` (modify)

**Analog:** itself (lines 147-158):
```tsx
<div role="row" data-testid={"watchlist-row-" + ticker} tabIndex={0}
  onClick={() => onSelect(ticker)}
  onKeyDown={(e) => e.key === "Enter" && onSelect(ticker)}
  className={"flex h-8 cursor-pointer ... " + (selected ? "border-l-primary bg-row-hover" : "border-l-transparent")}>
```
Changes: add `aria-selected={selected}`; Space also selects (`e.key === "Enter" || e.key === " "` with `preventDefault`); each span gets `role="cell"`; add remove `<button data-testid={"watchlist-remove-" + ticker}>` visible on `group-hover`/`focus-visible` (add `group` class), with `onClick` calling `e.stopPropagation()` then `onRemove(ticker)`.

### `frontend/src/components/Terminal.tsx` (modify)

**Analog:** itself (lines 188-199 of dump). Replace `useState("AAPL")` with selection derived from `useWatchlist` rows (AAPL if present on first load, else first row, else `""`; reset to first remaining when selected is removed). Replace the main-chart `Panel` placeholder: keep `testId="main-chart"` and `data-ticker={selected}` (existing prop passes via `...rest` in Panel), render `<MainChart ticker={selected} points={chart[selected] ?? []} />`. Panel bodies use `--color-bg` (Panel.tsx currently `bg-surface` on the section; make section chrome surface and body `bg-bg`; confirm token name in `globals.css`).

---

## Shared Patterns

### Async/blocking discipline
**Source:** CONTEXT.md decisions. **Apply to:** `watchlist.py`, `main.py` lifespan: every sqlite call via `await asyncio.to_thread(db.fn, ...)`.

### Module style
**Source:** `app/api/health.py`, `stream.py`. One-line module docstring, docstring per function, no emojis, short functions, full `/api/...` paths in decorators, routers built with factory when they need `cache`/`source`.

### Test conventions
**Source:** `backend/tests/market/test_stream.py`. Async tests with no decorator (auto mode), one-line docstring per test, fixtures as plain functions.

### Frontend conventions
**Source:** `usePriceStream.ts`, `Watchlist.tsx`. `"use client"` where hooks used, `@/` path alias, inline props typing, Tailwind v4 token classes (`bg-surface`, `border-border`, `text-text-muted`, `text-up`, `text-down`, `bg-row-hover`, `border-l-primary`), `data-testid` strings built as `"prefix-" + ticker`.

### Gates
Backend: `cd backend && uv run pytest tests -x -q`. Frontend: `npm run lint && npm run typecheck && npm run build` from `/mnt/c/...` cwd. Verify on port 8010+, stop by PID.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/db/schema.sql` | config | batch | No SQL/DB code in repo; use RESEARCH.md |
| `backend/app/db.py` | repository | CRUD | No sqlite code in repo; use RESEARCH.md Pattern 1 and init_db |
| `frontend/src/components/WatchlistAddForm.tsx` | component | request-response | No form/input in repo; use UI-SPEC |
| `frontend/src/components/MainChart.tsx` (core) | component | streaming | No chart-lib component yet; use RESEARCH.md Pattern 4 |

## Metadata

**Analog search scope:** `backend/app/**`, `backend/tests/**`, `frontend/src/**`
**Files scanned:** ~32 tracked files in backend/ and frontend/ (read: main.py, health.py, stream.py, interface.py, test_health.py, part of test_stream.py, pyproject test config, all listed frontend src files)
**Pattern extraction date:** 2026-10-19
