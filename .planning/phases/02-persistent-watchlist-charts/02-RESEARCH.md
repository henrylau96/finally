# Phase 2: Persistent Watchlist & Charts - Research

**Researched:** 2026-10-19
**Domain:** stdlib sqlite3 + FastAPI REST, React 19 + Lightweight Charts 5.2
**Confidence:** HIGH (backend, from code read + stdlib knowledge), MEDIUM-HIGH (LWC behavior, from official API docs)

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Stdlib `sqlite3` with small repository functions; async routes call them via `asyncio.to_thread`.
- `DB_PATH` env var, default `<repo>/db/finally.db` (Dockerfile already sets `DB_PATH=/app/db/finally.db`); create parent dir if missing.
- Initialize in app lifespan: execute `backend/db/schema.sql` (`CREATE TABLE IF NOT EXISTS`), then seed if `users_profile` is empty.
- All six PLAN.md tables now, PLAN.md columns, `user_id` default `"default"`, UNIQUE (user_id, ticker) on watchlist and positions.
- Ticker trimmed + uppercased, must match `^[A-Z]{1,5}$` else 422. Simulator gives unknown symbols a 50-300 seed price.
- `GET /api/watchlist` -> list of `{ticker, price, previous_price, direction, day_change_pct, added_at}`; price fields null until the ticker has ticked.
- `POST /api/watchlist {ticker}` -> 201 with row; duplicate -> 200 with existing row (no second row).
- `DELETE /api/watchlist/{ticker}` -> 204; 404 when not watched.
- Startup loads watchlist tickers from DB into the market source (replacing `DEFAULT_TICKERS` at runtime). Add/remove update DB, source, cache together. Frontend rows come from `GET /api/watchlist` on load and after each add/remove, replacing `frontend/src/lib/tickers.ts`.
- UI: add control (`watchlist-add-input`, `watchlist-add-button`, purple), per-row remove `watchlist-remove-{TICKER}`, Lightweight Charts 5.2 area chart from a ~1000-point client buffer (separate from 120-point sparkline buffer), `main-chart` with `data-ticker`, default AAPL, click/Enter/Space selects. Fold in Phase 1 UI-review fixes (fixed-height notice slot, `--color-bg` panel bodies, grid roles + `aria-selected`, Space selects, Reconnecting precedence).
- Tablet auto-collapse of chat dock stays in Phase 6.

### Claude's Discretion
Module split inside `backend/app/db/` vs `backend/db/`, router file names, frontend data-fetch helper shape, chart styling within UI-SPEC tokens.

### Deferred Ideas (OUT OF SCOPE)
- Tablet auto-collapse of chat dock (UI-13, Phase 6)
- Dotted symbols like BRK.B

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | SQLite created + seeded at first start | Lifespan init: mkdir, WAL, executescript(schema.sql), seed-if-empty |
| DATA-02 | Six tables, user_id default "default" | schema.sql in section Code Examples |
| DATA-03 | Seed user $10k + 10 tickers | `INSERT OR IGNORE` seed in same init txn |
| WATCH-01 | GET /api/watchlist with prices | Join DB rows with `cache.get`, null when uncached |
| WATCH-02 | POST add, starts streaming | DB insert then `source.add_ticker`; 201 |
| WATCH-03 | DELETE remove | DB delete then `source.remove_ticker` (also clears cache); 204/404 |
| WATCH-04 | Duplicate handled | `INSERT OR IGNORE` + rowcount; 200 with existing row |
| UI-05 | Add/remove in UI | Refetch pattern, form/pending/error contract from UI-SPEC |
| UI-06 | Click ticker -> main chart | LWC AreaSeries component, 1000-pt buffer, second-dedupe |
</phase_requirements>

## Summary

Phase 1 left a clean seam: `main.py` has module-level `cache` and `source`, a lifespan that calls `source.start(DEFAULT_TICKERS)`, and routers built by factory (`create_stream_router(cache)`). Phase 2 adds `app/db.py` (sqlite helpers), `backend/db/schema.sql`, and `app/api/watchlist.py` with `create_watchlist_router(cache, source)`. Lifespan order: `init_db()` (via `to_thread`) -> `list_tickers()` -> `source.start(tickers)`. `source.start` already seeds the cache for each ticker, and `add_ticker`/`remove_ticker` already write/clear the cache, so the API handler only has to touch DB then source.

The frontend adds one dependency (`lightweight-charts` 5.2.1), a `useWatchlist` hook (fetch + add + remove, refetch), a deeper 1000-point buffer keyed by time-in-seconds in `usePriceStream`, and a `MainChart` component. The one real gotcha is time handling: SSE ticks arrive every 500ms, and LWC requires strictly ascending integer-second times in `setData` and non-decreasing in `update` (equal replaces the last bar). Collapse by `Math.floor(timestamp)` and keep a last-time guard.

**Primary recommendation:** connection-per-call sqlite (no shared connection), router factory pattern like stream.py, `series.update()` with floored seconds, one `useEffect` to create the chart (cleanup `chart.remove()`) and a separate effect to set/update data.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Watchlist persistence | Database | API | SQLite is source of truth across restarts |
| Streamed ticker set | API / Backend | — | Source add/remove driven by API handler |
| Latest price for list | API (cache) | — | `GET /api/watchlist` reads in-memory cache |
| Input validation | API (pydantic) | Browser | Server authoritative (422); client regex avoids round-trip |
| Chart history buffer | Browser | — | "since page load" from SSE; no server history this phase |
| Chart rendering | Browser (canvas) | — | Lightweight Charts |
| Selection state | Browser | — | In-memory only |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 (stdlib, Python 3.14) | stdlib | DB | Locked decision |
| fastapi | >=0.146.0 (installed) | REST | Existing |
| pydantic v2 (via fastapi) | existing | request validation | `field_validator` |
| lightweight-charts | 5.2.1 (latest, modified 2026-08-12) | main chart | Locked in UI-SPEC; Apache-2.0, TradingView official [VERIFIED: npm view lightweight-charts] |

No other new dependencies. No python deps added (`httpx`, `pytest-asyncio` already dev deps).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| connection-per-call | one shared conn `check_same_thread=False` | Shared conn needs a lock under to_thread concurrency; per-call is simpler and cheap for a local file |
| Recharts | — | Locked out |

**Installation:**
```bash
cd /mnt/c/Users/fulai/projects/finally/frontend && npm install lightweight-charts@5.2.1
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| lightweight-charts | npm | multi-year (v5.2.1, 2026-08) | high (TradingView official) | github.com/tradingview/lightweight-charts | not run (slopcheck is a pip tool; skipped to keep scope small) | Approved: named in locked UI-SPEC and official docs (tradingview.github.io/lightweight-charts); `npm view` shows license Apache-2.0 and no postinstall script |

**Packages removed:** none. **Flagged suspicious:** none.

## Architecture Patterns

### System Architecture Diagram

```
startup lifespan
  init_db(DB_PATH) -> schema.sql + seed-if-empty
        |
  list_tickers() --> source.start(tickers) --> cache seeded, sim loop running

browser                          FastAPI                         state
  GET /api/watchlist  ---------> to_thread(list_rows) -> merge cache.get(t) -> JSON
  POST /api/watchlist {ticker} -> validate -> to_thread(insert) -> created? source.add_ticker -> 201 / 200
  DELETE /api/watchlist/{T}  --> to_thread(delete) -> deleted? source.remove_ticker -> 204 / 404
  EventSource /api/stream/prices <-- cache snapshot (all tickers) every change
  useWatchlist(refetch) -> rows; usePriceStream -> quotes/history/chartBuffer -> MainChart(createChart/AreaSeries)
```

### Recommended Project Structure
```
backend/
├── db/schema.sql              # DDL (+ optional seed.sql)
├── app/db.py                  # connect(), init_db(), list_watchlist(), add_ticker(), remove_ticker()
├── app/api/watchlist.py       # create_watchlist_router(cache, source)
├── app/main.py                # lifespan ordering; include router
└── tests/test_db.py, tests/test_watchlist_api.py
frontend/src/
├── lib/useWatchlist.ts        # fetch/add/remove + refetch
├── lib/usePriceStream.ts      # + chart buffer (per ticker {time,value}[] <=1000)
├── components/MainChart.tsx   # LWC wrapper
├── components/WatchlistAddForm.tsx
```
Delete `lib/tickers.ts` (WR-03). Note `backend/db/` is a data/SQL dir (not a Python package); Python code lives in `app/db.py`, which loads `Path(__file__).parents[1] / "db" / "schema.sql"`. Default DB path: `Path(__file__).parents[2] / "db" / "finally.db"` (app -> backend -> repo) [VERIFIED: file layout].

### Pattern 1: sqlite3 with asyncio.to_thread (connection per call)
**What:** each repository function opens its own connection, uses it, closes. Safe across worker threads (no sharing, no `check_same_thread` issue). Set WAL once in `init_db` (persists in the file). Use `timeout=5` default busy wait. Python 3.12+ also supports `autocommit=`; keep default and use `with conn:` for commit.
```python
# Source: Python sqlite3 docs (stdlib); pattern is [ASSUMED] best practice, simple and correct
import sqlite3
from contextlib import closing

def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def add_ticker(path, ticker) -> tuple[dict, bool]:
    """Insert ticker; return (row, created)."""
    with closing(connect(path)) as conn, conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, 'default', ?, ?)",
            (str(uuid4()), ticker, datetime.now(UTC).isoformat()))
        row = conn.execute("SELECT ticker, added_at FROM watchlist WHERE user_id='default' AND ticker=?", (ticker,)).fetchone()
        return dict(row), cur.rowcount == 1
```
Note `with closing(conn), conn` : `closing` closes; `conn` as context manager commits/rolls back (it does NOT close). Order `closing(...) as conn, conn` is correct.

Routes: `await asyncio.to_thread(db.add_ticker, db_path(), ticker)`. Read `DB_PATH` at call time through a `db_path()` helper (`Path(os.environ.get("DB_PATH", DEFAULT))`) so tests can `monkeypatch.setenv` per test.

### Pattern 2: Lifespan ordering
```python
@asynccontextmanager
async def lifespan(app):
    end_streams_on_exit_signal()
    await asyncio.to_thread(db.init_db)
    tickers = await asyncio.to_thread(db.list_tickers)
    await source.start(tickers)
    yield
    await source.stop()
```
`source.start([])` with an empty list: GBMSimulator with zero tickers makes `rng.standard_normal(0)` - harmless, `_cholesky` None; verify in a test (empty watchlist after user removes all is a real state). Add a test for it. [VERIFIED: simulator.py reads: n<2 -> cholesky None; step on empty dict returns {}]

Because init is in lifespan (not import), the existing `tests/test_health.py` (ASGITransport, no lifespan) stays valid; but watchlist API tests need lifespan (see Validation).

### Pattern 3: FastAPI responses and validation
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
    if not await asyncio.to_thread(db.remove_ticker, db.db_path(), ticker.strip().upper()):
        raise HTTPException(404, "Ticker not on watchlist")
    await source.remove_ticker(ticker.strip().upper())
```
`ValueError` in a pydantic v2 validator produces 422 automatically. A `status_code=204` route that returns `None` sends no body in current FastAPI. Setting `response.status_code` on an injected `Response` overrides the decorator default [CITED: fastapi.tiangolo.com/advanced/response-change-status-code]. Lowercase path `aapl` DELETE: normalize with upper.

`GET` item builder: `u = cache.get(t)`; `{"ticker", "price": u.price if u else None, "previous_price", "direction", "day_change_pct", "added_at"}` (nulls when no u). Order: `ORDER BY added_at, rowid`.

**Race notes:** `source.add_ticker/remove_ticker` run on the event loop alongside `_run_loop` (no awaits inside), so no lock needed. If the source is stopped (tests without lifespan) `self._sim` is None -> AttributeError; tests must run lifespan. Also a tick can arrive in between DB delete and cache removal; harmless.

### Pattern 4: Lightweight Charts 5.2 in React 19
```tsx
// Source: tradingview.github.io/lightweight-charts (v4->v5 migration, ISeriesApi, React tutorial)
import { AreaSeries, CrosshairMode, LineStyle, createChart, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";

useEffect(() => {
  const chart = createChart(containerRef.current!, { autoSize: true, layout: {...}, grid: {...}, ... });
  const series = chart.addSeries(AreaSeries, { lineColor: "#209dd7", topColor: "rgba(32,157,215,0.28)", bottomColor: "rgba(32,157,215,0)", lineWidth: 2 });
  chartRef.current = chart; seriesRef.current = series;
  return () => { chart.remove(); chartRef.current = null; seriesRef.current = null; };
}, []);   // create once; StrictMode double-mount creates/removes/creates cleanly

useEffect(() => {          // ticker switch: replace data
  seriesRef.current?.setData(points);   // points: {time: UTCTimestamp, value}[] strictly ascending
  chartRef.current?.timeScale().fitContent();
}, [ticker]);

// live ticks: seriesRef.current.update({ time, value }) for the newest point only
```
- `autoSize: true` makes LWC attach its own ResizeObserver; no manual listener needed. The container must have non-zero size (give it `h-full w-full`/`min-h-0` in the panel; a 0-height flex child yields an invisible chart). [CITED: LWC createChart options docs; ASSUMED on the sizing caveat from experience]
- `update(bar)`: "updates the latest item if times of the passed/latest items are equal"; time must be >= latest; older time throws unless `historicalUpdate` true [CITED: ISeriesApi docs]. `setData` expects ascending order; duplicates in the array are not documented as safe - dedupe before calling (library asserts "data must be asc ordered by time" in dev builds).
- Time: pass `Math.floor(timestamp) as UTCTimestamp`. Local-time axis: LWC displays UTC by default; the UI-SPEC wants local HH:mm:ss via `localization.timeFormatter: (t) => new Date((t as number) * 1000).toLocaleTimeString("en-GB")`. Tick-mark labels on the axis still use UTC unless you also set `timeScale.tickMarkFormatter`; set both to the same local formatter. [ASSUMED - verify in browser during E2E/visual check]
- Do not call `fitContent()` on each tick (resets user pan/zoom); only on ticker switch.
- Mount-only effect with SSR: `next build` with `output: "export"` prerenders client components; `createChart` runs only in `useEffect` so it is safe, but a top-level `import "lightweight-charts"` is fine (no `window` access at import time) [ASSUMED; confirm by `npm run build`].
- Empty state: UI-SPEC overlays `main-chart-empty` while < 2 points; keep the chart container mounted underneath so the chart object persists (do not conditionally unmount the container).

### Pattern 5: Frontend buffer for chart (time-in-second dedupe)
In `usePriceStream`, keep `chart: Record<string, {time:number; value:number}[]>`; per message and ticker:
```ts
const t = Math.floor(q.timestamp);
const arr = prev[ticker] ?? [];
const last = arr[arr.length - 1];
if (last && t < last.time) skip;            // out-of-order guard
else if (last && t === last.time) replace last value;
else append; then slice(-1000)
```
The same ticker can appear unchanged in later snapshots (SSE sends a full snapshot when any ticker changed) - the dedupe by second handles it. Also prune keys for tickers no longer on the watchlist (UI-SPEC: removal drops buffers); simplest: when building next state, only keep tickers present in the incoming snapshot (the cache removes them, and the stream snapshot omits them). The existing `history` code already does this via `Object.fromEntries(Object.entries(next)...)`. Caveat: a removed ticker can linger in `quotes`? `quotes` also derived from `next`, so it drops. Good.

To avoid a second copy of every tick in React state at 2 Hz x 10 tickers x 1000 points, it is fine (10k points); but each setState copies arrays. Acceptable; if sluggish, keep buffers in a `useRef` and bump a version. Keep simple first.

MainChart receives `points` for the selected ticker only. On ticker switch effect `setData(points)` then per-tick effect does `update(lastPoint)`. Use a ref of the last-applied time to skip stale updates and avoid the "Cannot update oldest data" error; after switching ticker, reset the ref to the last time of the set data.

### Pattern 6: Watchlist refetch
`useWatchlist()` returns `{rows, loading, error, add, remove}`; `add` POSTs then `await load()`; `remove` DELETEs (treat 204 and 404 as removed) then `await load()`. Terminal owns `selected`; `useEffect` on rows: if selected not in rows -> first row's ticker or `""`. Default selection: AAPL if present in first load else first row.

Dev note: `next dev` rewrites `/api` to `localhost:8000` (user's old container!). For dev verification either build static into `backend/static` and run uvicorn on 8010+ (preferred, as in Phase 1), or temporarily point the rewrite; do not change the committed rewrite port without telling the user.

### Anti-Patterns to Avoid
- Calling sqlite in an `async def` directly (blocks loop).
- Sharing one `sqlite3.Connection` across `to_thread` calls without `check_same_thread=False` + lock.
- Module-level DB init at import (breaks tests, path resolved too early).
- `chart.remove()` omitted on cleanup (StrictMode leaks a second chart/canvas).
- `fitContent()` per tick; `setData` per tick (flicker, reset zoom).
- Returning `{"ticker": ...}` from 204 route (body with 204).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ticker validation 422 | manual regex + HTTPException | pydantic `field_validator` | automatic 422 shape |
| Chart resize | custom ResizeObserver/window listener | `autoSize: true` | built in |
| Price/time axis formatting | custom canvas labels | `localization.priceFormatter/timeFormatter` | built in |
| Migrations | Alembic | `CREATE TABLE IF NOT EXISTS` | locked decision |
| UUIDs | custom | `uuid.uuid4()` | stdlib |

## Runtime State Inventory

Not a rename/migration phase. One relevant note: an existing `db/finally.db` may exist from an earlier prior build or old container (directory `db/` currently contains only `.gitkeep` [VERIFIED: ls]). `CREATE TABLE IF NOT EXISTS` would not alter a pre-existing differently-shaped table; low risk, none present.

## Common Pitfalls

### Pitfall 1: Two ticks in the same second (LWC duplicate/out-of-order)
**What goes wrong:** `setData` with equal times asserts; `update` with older time throws.
**How to avoid:** floor to seconds, replace-on-equal, skip-on-older in buffer (Pattern 5); same logic guards the `update()` call.
**Warning signs:** console error "Cannot update oldest data" / "data must be asc ordered".

### Pitfall 2: Zero-size chart container
Chart with `autoSize` renders nothing if parent has no height. Panel body is `flex-1 min-h-0 overflow-auto`; put chart wrapper at `relative h-full`, and make the Panel body not scroll for the chart.

### Pitfall 3: Lifespan not running in tests
`httpx.ASGITransport` does not run lifespan; `source._sim` is None and DB uninitialized. Wrap with `async with app.router.lifespan_context(app):` in a fixture (or `with TestClient(app)`).

### Pitfall 4: Module-level `cache`/`source` shared across tests
After one test adds a ticker, the next sees it in the cache. DB is fresh per test (tmp_path) and lifespan `start` builds a new sim, but the old cache entries persist. Fix: in the fixture, construct state via a small `create_app()`-style approach, or clear the cache (`for t in list(cache.get_all()): cache.remove(t)`) before entering lifespan. Prefer minimal change: keep module-level objects, clear cache in the fixture.

### Pitfall 5: Empty watchlist
Source with zero tickers, `GET` returns `[]`, frontend shows "No tickers yet", SSE sends snapshot `{}` (version changes on removal). Frontend `Object.entries({})` fine; the Notice "Waiting for prices" must not show forever for an empty list (UI-SPEC precedence item 6).

### Pitfall 6: Re-adding a previously removed ticker
Simulator reseeds from `SEED_PRICES` or a new random 50-300 (so price jumps) and cache `_opens` was cleared on remove (day change resets). Acceptable; note it.

### Pitfall 7: Stale rows vs SSE
SSE may deliver a quote for a just-removed ticker briefly; row rendering is driven by the watchlist rows, not quotes, so no ghost row.

### Pitfall 8: `lightweight-charts` and Next static export
Chart code must be in a `"use client"` component and only touch DOM in effects.

### Pitfall 9: Windows wrappers
`npm install` runs via Windows wrapper; cwd must be under /mnt/c. E2E: Playwright browsers live in `test/`; verification on port 8010+.

## Code Examples

### schema.sql (DATA-02)
```sql
CREATE TABLE IF NOT EXISTS users_profile (
  id TEXT PRIMARY KEY DEFAULT 'default',
  cash_balance REAL NOT NULL DEFAULT 10000.0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS watchlist (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL DEFAULT 'default',
  ticker TEXT NOT NULL,
  added_at TEXT NOT NULL,
  UNIQUE (user_id, ticker)
);
CREATE TABLE IF NOT EXISTS positions (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default', ticker TEXT NOT NULL,
  quantity REAL NOT NULL, avg_cost REAL NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE (user_id, ticker)
);
CREATE TABLE IF NOT EXISTS trades (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default', ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('buy','sell')), quantity REAL NOT NULL,
  price REAL NOT NULL, executed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
  total_value REAL NOT NULL, recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
  role TEXT NOT NULL CHECK (role IN ('user','assistant')), content TEXT NOT NULL,
  actions TEXT, created_at TEXT NOT NULL
);
```
`users_profile` has no `user_id` column per PLAN.md (its `id` is the user id); DATA-02 "every table carries user_id" is satisfied by `id` default `'default'` for that table - flag to planner (see Assumptions A2). Add `ORDER BY` indexes unnecessary.

### init_db + seed
```python
def init_db() -> None:
    path = db_path(); path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as conn, conn:
        conn.execute("PRAGMA journal_mode=WAL")      # persistent file setting; do outside txn if error
        conn.executescript(SCHEMA.read_text())
        if conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 0:
            now = datetime.now(UTC).isoformat()
            conn.execute("INSERT INTO users_profile (id, cash_balance, created_at) VALUES ('default', 10000.0, ?)", (now,))
            conn.executemany("INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, 'default', ?, ?)",
                             [(str(uuid4()), t, now) for t in DEFAULT_TICKERS])
```
Seed watchlist only on empty `users_profile` (not on empty watchlist), otherwise a user who removed all tickers gets them back on restart. Distinct `added_at` ordering: seed rows share one timestamp; order by `rowid` secondary, or give each i microseconds. Use `ORDER BY rowid` (insertion order) - simplest and stable.
`executescript` issues an implicit COMMIT first; run `PRAGMA journal_mode=WAL` before it (it cannot change inside a transaction) — put the PRAGMA on its own, before `with conn`. WAL: optional for single-user; recommended because the 30s snapshot task (Phase 3) and API reads overlap. Creates `-wal`/`-shm` files next to the DB: `.gitignore` has `db/*.db` only; add `db/*.db-wal`, `db/*.db-shm` (or `db/*.db*`). [VERIFIED: .gitignore line 210]

### Pytest fixture
```python
@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    for t in list(main.cache.get_all()): main.cache.remove(t)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            yield c
```
Plain REST works with ASGITransport (only infinite SSE does not). Lifespan also installs signal handlers (`end_streams_on_exit_signal`) each time - chains repeatedly across tests (handler chain grows, harmless but note; main-thread only: pytest runs in main thread, OK).

## State of the Art

| Old | Current | Impact |
|-----|---------|--------|
| `chart.addAreaSeries()` (v4) | `chart.addSeries(AreaSeries, opts)` (v5) | must use v5 form [CITED: LWC v4->v5 migration] |
| manual resize listener | `autoSize: true` | no listener |
| `@app.on_event` | lifespan | already used |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Local-time axis needs both `localization.timeFormatter` and `timeScale.tickMarkFormatter` | Pattern 4 | Axis labels show UTC; visual-only, verify in browser |
| A2 | `users_profile` uses `id` (not `user_id`) per PLAN.md; satisfies DATA-02 | schema | Verifier may expect a `user_id` column; trivial to add if the user wants |
| A3 | `createChart` import is SSR-safe in Next 16 static export | Pitfall 8 | Build fails; fallback `dynamic(() => import(...), {ssr:false})` |
| A4 | connection-per-call is adequate (no pooling needed) | Pattern 1 | None for a local single-user file |
| A5 | Duplicate times in `setData` assert/misbehave; we dedupe regardless | Pattern 4 | None (we dedupe either way) |

## Open Questions

1. **Where does `schema.sql` live?** RESOLVED: `backend/db/schema.sql` per CONTEXT/PLAN §4; loaded from `app/db.py` via `Path(__file__).parents[1] / "db"`. Dockerfile copies `backend/` wholesale (verify the Dockerfile `COPY` includes it in Phase 6).
2. **Order of the watchlist list?** RESOLVED: UI-SPEC says `added_at` ascending; implement as `ORDER BY rowid`.
3. **Remove while selected?** RESOLVED by UI-SPEC: first remaining row, else empty string.
4. **Should DELETE 404 be treated as removed in UI?** RESOLVED by UI-SPEC: yes.
5. **Should the stream be limited to the watchlist when a ticker is removed?** RESOLVED by CONTEXT: remove from source+cache; Phase 3 widens for positions.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv / Python 3.14 | backend | yes | per project | — |
| node/npm (Windows wrappers) | frontend | yes | npm view worked | — |
| npm registry | install lightweight-charts | yes | 5.2.1 | — |
| Playwright (in test/) | E2E 02-watchlist | node_modules present in `test/` | — | run pytest + curl if browsers unavailable |
| Free port 8010+ | verification | yes (8000 is user's container) | — | pick another |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9 + pytest-asyncio (auto mode), httpx ASGITransport |
| Config file | `backend/pyproject.toml` |
| Quick run | `cd backend && uv run pytest tests -x -q` |
| Full suite | same + `cd frontend && npm run lint && npm run typecheck && npm run build` |
| E2E (manual gate) | `test/e2e/02-watchlist.spec.ts` against a server on 8010+ |

### Phase Requirements -> Test Map
| Req | Behavior | Type | Automated Command | Exists? |
|-----|----------|------|-------------------|---------|
| DATA-01 | DB file + parent dir created on first start; second init does not reseed | unit | `uv run pytest tests/test_db.py::test_init_creates_and_is_idempotent -x` | Wave 0 |
| DATA-02 | six tables exist; `user_id` default 'default' | unit | `uv run pytest tests/test_db.py::test_schema_tables -x` (query `sqlite_master`, `PRAGMA table_info`) | Wave 0 |
| DATA-03 | seed: cash 10000, 10 tickers in order | unit | `uv run pytest tests/test_db.py::test_seed -x` | Wave 0 |
| WATCH-01 | GET returns 10 rows w/ 6+ keys; price non-null after start | api | `uv run pytest tests/test_watchlist_api.py::test_list -x` | Wave 0 |
| WATCH-02 | POST 201, row in GET, ticker in `source.get_tickers()` and cache; lowercase accepted; `"TOOLONG"`, `"A1"`, `""` -> 422 | api | `uv run pytest tests/test_watchlist_api.py -k "add or invalid" -x` | Wave 0 |
| WATCH-03 | DELETE 204, gone from GET/source/cache; second DELETE 404; persists across lifespan restart | api | `uv run pytest tests/test_watchlist_api.py -k "remove or persist" -x` | Wave 0 |
| WATCH-04 | duplicate POST 200, single row | api | `uv run pytest tests/test_watchlist_api.py::test_duplicate -x` | Wave 0 |
| empty list | all removed -> GET `[]`; restart with empty watchlist does not reseed | api | `-k empty` | Wave 0 |
| UI-05 | add form/remove button/empty state compile; test ids present | build+grep | `cd frontend && npm run lint && npm run typecheck && npm run build && grep -rl "watchlist-add-input" out/ && grep -rl "watchlist-remove-" out/` (build output under `frontend/out`; check that chunk grep finds the strings) | Wave 0 |
| UI-06 | chart component built, `main-chart` + `data-ticker` present, no `Coming soon` | build+grep | `grep -rl "lightweight-charts" frontend/package.json; ! grep -r "Select a ticker to see its chart" frontend/src` | Wave 0 |
| UI-05/06 live | add PYPL -> price, remove, select MSFT | e2e | start server: `cd backend && STATIC_DIR=... DB_PATH=/tmp-scratch/e2e.db uv run uvicorn app.main:app --port 8010`, then curl: `curl -s -XPOST localhost:8010/api/watchlist -H 'content-type: application/json' -d '{"ticker":"pypl"}' -w '%{http_code}'` (201), repeat (200), `curl -XDELETE .../PYPL` (204), again (404); Playwright `BASE_URL=http://localhost:8010 npx playwright test 02-watchlist` from `test/` | manual/E2E |

Stop servers by explicit PID (`kill <pid>`), never `pkill -f uvicorn`.

### Sampling Rate
- Per task commit: `cd backend && uv run pytest tests -x -q` and (frontend tasks) `npm run typecheck && npm run lint`
- Per wave merge: full backend suite + `npm run build`
- Phase gate: full suite + curl smoke on 8010 + Playwright 02 spec

### Wave 0 Gaps
- [ ] `backend/tests/test_db.py`
- [ ] `backend/tests/test_watchlist_api.py` (+ conftest fixture with lifespan and tmp DB)
- [ ] `.gitignore` entries for `db/*.db-wal`, `db/*.db-shm`
- [ ] No frontend unit-test framework exists (no vitest/jest in package.json); gates are lint/typecheck/build + Playwright. Do not add one this phase (PLAN §12 mentions RTL; defer, flag to user).

## Security Domain

### Applicable ASVS Categories
| Category | Applies | Control |
|----------|---------|---------|
| V2/V3 Auth/Session | no (single-user by design) | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | pydantic validator `^[A-Z]{1,5}$`; path param normalized and used only as a bound SQL parameter |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| SQL injection via ticker | Tampering | parameterized queries only (`?`), never f-string SQL |
| Unbounded watchlist growth / DoS via add | DoS | optional cap (e.g. 50) - not required; mention to planner as discretionary |
| XSS via ticker in DOM | Tampering | regex limits to A-Z; React escapes anyway |
| DB path from env | Info | trusted deployment config |

## Sources

### Primary (HIGH)
- npm registry: `npm view lightweight-charts` -> 5.2.1, Apache-2.0, modified 2026-08-12
- LWC docs: tradingview.github.io/lightweight-charts (v4->v5 migration; ISeriesApi `update`/`setData`; React simple tutorial) - fetched this session
- Repo code read: `backend/app/main.py`, `market/*`, `api/stream.py`, `tests/`, `frontend/src/**`, E2E spec/helpers, `.gitignore`

### Secondary (MEDIUM)
- FastAPI/pydantic/sqlite3 behaviors from training knowledge, consistent with Phase 1 research of FastAPI 0.146 [ASSUMED where not tagged]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - one dependency, version verified
- Architecture: HIGH - follows existing seams
- Pitfalls: MEDIUM-HIGH - LWC time rules cited; axis-timezone detail assumed

**Research date:** 2026-10-19
**Valid until:** 2026-11-19
