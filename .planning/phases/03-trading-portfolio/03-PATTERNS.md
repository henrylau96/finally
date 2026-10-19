# Phase 3: Trading & Portfolio - Pattern Map

**Mapped:** 2026-10-19
**Files analyzed:** 27 (new and modified)
**Analogs found:** 25 / 27 (treemap.ts and the snapshot loop have only RESEARCH.md sketches)

Line numbers refer to the current repo. Deeper code (execute_trade, squarify, toSeries, derivePositions, trade route) is already in 03-RESEARCH.md Patterns 1-8 and "Code Examples"; this file only maps analogs and shows what to copy.

## File Classification

| File | Role | Data Flow | Closest Analog | Match |
|------|------|-----------|----------------|-------|
| `backend/app/portfolio.py` (new) | service/repository | CRUD (txn) + batch (snapshot) | `backend/app/db.py` | role-match |
| `backend/app/api/portfolio.py` (new) | route (router factory) | request-response | `backend/app/api/watchlist.py` | exact |
| `backend/app/api/watchlist.py` (mod: reconcile_stream on DELETE, shared Ticker type) | route | request-response | itself | exact |
| `backend/app/main.py` (mod: lifespan union, snapshot task, trade_lock, include router) | config/lifespan | event-driven | itself (lifespan lines 100-107) | exact |
| `backend/app/streaming.py` or in portfolio.py (new: reconcile_stream) | service | request-response | `watchlist.py` add/remove calls | partial |
| `backend/tests/test_portfolio.py`, `test_portfolio_api.py`, `test_snapshots.py`, `test_streaming_union.py` (new) | test | request-response | `backend/tests/test_watchlist_api.py` + `conftest.py` | exact |
| `backend/tests/conftest.py` (mod: seed_position helper) | test fixture | CRUD | itself | exact |
| `frontend/src/lib/usePortfolio.ts` (new) | hook | request-response | `lib/useWatchlist.ts` | exact |
| `frontend/src/lib/portfolio.ts` (new: derivePositions, pnlState, toSeries) | utility | transform | `lib/format.ts`, `appendPoint` in `usePriceStream.ts:21` | role-match |
| `frontend/src/lib/treemap.ts` (new) | utility | transform | none (RESEARCH Pattern 7) | none |
| `frontend/src/lib/chartTheme.ts` (new) | config | n/a | hex literals in `MainChart.tsx:16-49` | extract |
| `frontend/src/lib/format.ts` (mod: formatQty, signed money) | utility | transform | itself | exact |
| `frontend/src/components/TradeBar.tsx` (new) | component | request-response | `WatchlistAddForm.tsx` | exact |
| `frontend/src/components/PositionsTable.tsx` (new) | component | transform | `Watchlist.tsx` + `WatchlistRow.tsx` | exact |
| `frontend/src/components/Heatmap.tsx` (new) | component | transform | `Panel.tsx` + `Watchlist.tsx` (a11y), ResizeObserver none | partial |
| `frontend/src/components/PnlChart.tsx` (new) | component | request-response + chart | `MainChart.tsx` | exact |
| `frontend/src/components/MainChart.tsx` (mod: use chartTheme, share base options) | component | chart | itself | exact |
| `frontend/src/components/Panel.tsx` (mod: `active` prop) | component | n/a | itself | exact |
| `frontend/src/components/Header.tsx` (mod: props total/cash, stale muting) | component | n/a | itself | exact |
| `frontend/src/components/Terminal.tsx` (mod: 3-row center, shared selected, usePortfolio) | component | n/a | itself | exact |
| `frontend/src/components/Watchlist.tsx` (mod: pl-[10px] fix, active) | component | n/a | itself line 76 | exact |
| `frontend/src/components/WatchlistAddForm.tsx` (mod: refocus on failure) | component | n/a | itself lines 18-29 | exact |
| `test/e2e/helpers.ts` (mod: openApp waits for cash `$`) | test infra | n/a | itself lines 14-17 | exact |

## Pattern Assignments

### `backend/app/api/portfolio.py` (route, request-response)

**Analog:** `backend/app/api/watchlist.py`

Imports and validator to reuse (lines 3-24); extract `AddTicker.normalize` into a shared `Ticker` annotated type and import it from both routers:
```python
import asyncio
import re
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, field_validator
from app import db
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource

class AddTicker(BaseModel):
    ticker: str
    @field_validator("ticker")
    @classmethod
    def normalize(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{1,5}", v):
            raise ValueError("ticker must be 1-5 letters")
        return v
```
Factory and handler shape (lines 27-28, 48-55): `def create_portfolio_router(cache, source) -> APIRouter: router = APIRouter()` then `@router.post("/api/portfolio/trade") async def ...` with full `/api/...` paths, DB work via `await asyncio.to_thread(...)`, `raise HTTPException(code, msg)`. Strings-only ticker is already guaranteed by pydantic str (test params `True/False/123` -> 422); mirror for quantity (`true`, `"5"`, `0`, `-1`, `1.00001`, NaN). Route body: RESEARCH "Trade route sketch"; read lock from `request.app.state.trade_lock`.

Remove-path change (watchlist.py:57-62): replace `await source.remove_ticker(t)` with `await reconcile_stream(source, t)`.

### `backend/app/portfolio.py` (service, CRUD txn + snapshot)

**Analog:** `backend/app/db.py`

Imports/conn pattern (lines 1-10, 136-140, 168-174):
```python
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from uuid import uuid4
from app.db import connect, db_path   # connect sets row_factory = sqlite3.Row
...
with closing(connect(db_path())) as conn, conn:
    rows = conn.execute("SELECT ... WHERE user_id = 'default' ORDER BY rowid").fetchall()
return [dict(r) for r in rows]
```
Timestamps: `datetime.now(UTC).isoformat()`; ids: `str(uuid4())`; all queries parameterized with `user_id = 'default'`. For the trade use `closing(connect(...))` + explicit `BEGIN IMMEDIATE` + commit/rollback (RESEARCH Pattern 1) instead of `with conn`. Functions are sync and called via `asyncio.to_thread`. `PriceCache.get(t)` returns `PriceUpdate | None` with `.price` (cache.py:35). Snapshot loop shape: same `try/except Exception: logger.exception` per iteration as `SimulatorDataSource._run_loop` (backend/app/market/simulator_source.py).

### `backend/app/main.py` (lifespan)

**Analog:** itself (lines 100-107)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    end_streams_on_exit_signal()
    await asyncio.to_thread(db.init_db)
    tickers = await asyncio.to_thread(db.list_tickers)   # -> portfolio.streamed_tickers (watchlist then held)
    await source.start(tickers)
    yield
    await source.stop()
```
Add after `init_db`: `app.state.trade_lock = asyncio.Lock()`; after `source.start`: startup `record_snapshot`, `asyncio.create_task(portfolio.snapshot_loop(cache))`; on teardown `task.cancel()` + `contextlib.suppress(asyncio.CancelledError)` before `source.stop()`. Register with `app.include_router(create_portfolio_router(cache, source))` next to line 113 (before the `/` StaticFiles mount at line 115).

### Backend tests (new files)

**Analog:** `backend/tests/test_watchlist_api.py` and `conftest.py`

Fixture (conftest.py 11-27): `db_env` sets `DB_PATH` to tmp and empties `main.cache`; `client` runs `main.app.router.lifespan_context(main.app)` with `httpx.ASGITransport`. Test style: `async def test_x(client)` (asyncio_mode auto), docstring per test, `@pytest.mark.parametrize("bad", [...])` for 422 matrix, `from app.main import app, cache, source`, assert `source.get_tickers()` and `cache.get_all()` for streaming. Example (lines 18-35, 41-51):
```python
async def test_add(client):
    response = await client.post("/api/watchlist", json={"ticker": " pypl "})
    assert response.status_code == 201
    assert "PYPL" in source.get_tickers()
    assert cache.get("PYPL") is not None
```
Deterministic prices: `cache.update("AAPL", 100.0)` (simulator ticks every 0.5 s, so assert against the returned trade price or `await source.stop()`). Every `client` start writes one startup snapshot, so history tests expect >= 1 row. Concurrency test (`asyncio.gather` of two buys) requires the lock be created in lifespan (RESEARCH Pattern 2). Unit tests of pure sync functions (`execute_trade`, `history`) need only `db_env` plus `db.init_db()`.

### `frontend/src/lib/usePortfolio.ts` (hook, request-response)

**Analog:** `frontend/src/lib/useWatchlist.ts` (copy the stale-response `seq` pattern, lines 14-37, and the `string | null` error-return mutation pattern, lines 39-56)
```ts
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
const seq = useRef(0);
const load = useCallback(async () => {
  const id = ++seq.current;
  let data: T | null = null;
  try { const res = await fetch("/api/..."); if (res.ok) data = await res.json(); } catch {}
  if (id !== seq.current) return;
  if (data) setX(data);
  setLoading(false);
}, []);
useEffect(() => {
  // eslint-disable-next-line react-hooks/set-state-in-effect
  void load();
}, [load]);
```
Mutation: `res.status === 422` -> fixed copy; `!res.ok` -> for 400 read `detail` from JSON and return verbatim; catch -> "Could not place the trade. Try again."; on success `await load(); setVersion(v => v + 1); return null`. Do not clear previous data on refetch.

### `frontend/src/components/TradeBar.tsx` (component, request-response)

**Analog:** `frontend/src/components/WatchlistAddForm.tsx`

Copy structure: `"use client"`, `useRef` input, `pending` state, uppercase on change, Esc clears, classes (lines 18-29, 33-66):
```tsx
async function submit(e: React.FormEvent) {
  e.preventDefault();
  const ticker = value.trim().toUpperCase();
  if (!/^[A-Z]{1,5}$/.test(ticker)) return onError(INVALID);
  onError(""); setPending(true);
  const err = await onAdd(ticker);
  setPending(false);
  if (err) return onError(err);
  ...
}
<input data-testid=... type="text" maxLength={5} autoComplete="off" spellCheck={false}
  disabled={pending} onChange={(e) => { setValue(e.target.value.toUpperCase()); onError(""); }}
  onKeyDown={(e) => { if (e.key === "Escape") {...} }}
  className="h-8 flex-1 border border-border bg-bg px-2 font-mono text-sm uppercase" />
<button className="h-8 w-14 bg-submit text-sm font-semibold text-text hover:brightness-110 disabled:cursor-progress disabled:opacity-50">
```
Differences per UI-SPEC: both buttons `type="button"`, Sell outline `border border-submit hover:bg-[rgba(117,57,145,0.2)]`, 80px/96px input widths, `aria-busy` on the form, fixed 24px error slot always rendered with `role="alert" data-testid="trade-error"` element only when error exists, refocus quantity (on success AND failure), ticker follows the `selected` prop via an effect (`react-hooks/set-state-in-effect` disable comment as at Terminal.tsx:22).

### `frontend/src/components/PositionsTable.tsx` (component, transform)

**Analog:** `WatchlistRow.tsx` (row semantics lines 38-54) and `Watchlist.tsx` (grid/header lines 66-80)
```tsx
<div role="row" aria-selected={selected} data-testid={"position-row-" + ticker} tabIndex={0}
  onClick={() => onSelect(ticker)}
  onKeyDown={(e) => { if (e.key !== "Enter" && e.key !== " ") return; e.preventDefault(); onSelect(ticker); }}
  className={"group grid h-8 cursor-pointer grid-cols-[...] items-center gap-2 border-b border-l-2 border-b-border px-2 transition-colors duration-100 hover:bg-row-hover " +
    (selected ? "border-l-primary bg-row-hover" : "border-l-transparent")}>
  <span role="gridcell" className="font-mono font-semibold">{ticker}</span>
  <span role="gridcell" className="text-right"><PriceCell ticker={ticker} price={quote?.price} direction={quote?.direction} live={live} /></span>
  <span role="gridcell" className={"text-right font-mono tabular-nums " + color}>{formatPct(pct)}</span>
```
Header row: `role="grid" aria-label="Positions"` > `rowgroup` > `row` with `columnheader`s, classes `h-6 items-center border-b border-border px-2 text-xs font-semibold uppercase tracking-[0.05em] text-text-muted` plus `border-l-2 border-l-transparent` (replaces the off-scale `pl-[10px]`); make it `sticky top-0 bg-surface`. Grid template `64px minmax(56px,1fr) 80px 80px 80px 72px`. Color rule from WatchlistRow:28 `!live || !pct ? "text-text-muted" : pct > 0 ? "text-up" : "text-down"` (positions use sign-only muted for zero, not live-gated; spec says zero = muted). Reuse `PriceCell` for the Price column. Rows from `derivePositions(...)` sorted by market value desc.

### `frontend/src/components/PnlChart.tsx` (component, chart)

**Analog:** `frontend/src/components/MainChart.tsx`

Create-once/cleanup pattern (lines 64-81) and base options (lines 20-51):
```tsx
const host = useRef<HTMLDivElement>(null);
const chartRef = useRef<IChartApi | null>(null);
const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
useEffect(() => {
  const { chart, series } = createLineChart(host.current!);
  chartRef.current = chart; seriesRef.current = series;
  return () => { chart.remove(); chartRef.current = null; seriesRef.current = null; };
}, []);
```
Series: `chart.addSeries(LineSeries, { color, lineWidth: 2, ... })` (v5 form, as `addSeries(AreaSeries, ...)` at line 41). Extract the `createChart` options block (lines 22-40) into a shared helper using `chartTheme.ts` constants, then both charts call it. Overlay empty state like MainChart lines 117-126 (`absolute inset-0 flex ... bg-bg text-text-muted`, `role="status"`), but keep host div mounted. Put `data-testid="pnl-chart"` and `data-points` on the wrapper inside the panel (remove `testId` from the Panel in Terminal). Refetch: mount, `version` change, `setInterval(30_000)`, with a `seq` ref guard; `toSeries` from RESEARCH Pattern 8; baseline via `series.createPriceLine({price: 10000, ..., lineStyle: LineStyle.Dashed})`.

### `frontend/src/components/Heatmap.tsx` (component, transform)

**Analog:** `Panel.tsx` (`testId="heatmap"` already on the panel, Terminal.tsx:35) and `WatchlistRow.tsx` (clickable/keyboard handler). No ResizeObserver analog: write a small `useSize(ref)` hook. Layout from `squarify` (RESEARCH Pattern 7); absolute px/percent cells with `border border-bg` gutters; `data-pnl` from the rounded rule (`Math.abs(pct) < 0.005` is flat, matching `formatPct` in format.ts:6-10); empty state `heatmap-empty` with `flex h-full items-center justify-center`.

### `frontend/src/components/Panel.tsx` (mod)

Add `active?: boolean`. Per checker clarification, draw underline by inset box-shadow so the strip stays 24px: on the `<h2>` (line 19) add `shadow-[inset_0_-2px_0_var(--color-accent)]` when `active`. Pass `active` for Watchlist (find its Panel usage in `Watchlist.tsx`) and Main chart (Terminal.tsx:31).

### `frontend/src/components/Header.tsx` (mod)

Currently static `--` (lines 10, 14). Add props `total?: number`, `cash?: number`; render `{formatPrice(total)}` with `status !== "connected"` -> `text-text-muted`. Import `formatPrice` from `@/lib/format`.

### `frontend/src/components/Terminal.tsx` (mod)

- Replace placeholders (lines 12-14, 34-44) with `HeatMap`, `PositionsTable`, `PnlChart`; delete `Placeholder`.
- Center grid `grid-rows-[1.4fr_1fr]` (line 30) -> `grid-rows-[1.4fr_auto_1fr]`; bottom row `grid-cols-3` (line 34) -> `grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)_minmax(0,1fr)]`; insert `<TradeBar .../>` after the main chart Panel.
- Selection (lines 19-24): start `useState("")`, fall to AAPL or first row after load, and validate against `watchlist ∪ positions` (RESEARCH Pitfall 10).
- Wire `const { portfolio, refresh, trade, version } = usePortfolio()` and `derivePositions(portfolio, quotes)` into Header/PositionsTable/Heatmap; `useMemo` on `[portfolio, quotes]`.

### Folded fixes

- `Watchlist.tsx:76`: replace `px-2 pl-[10px]` with `px-2 border-l-2 border-l-transparent`.
- `WatchlistAddForm.tsx:18-29`: move `setTimeout(() => input.current?.focus())` before `if (err) return onError(err)` so it also runs on failure.
- `lib/format.ts`: add `formatQty` (up to 4 dp, trimmed) and a signed-dollars helper next to `formatPrice`/`formatPct` (lines 1-11), keeping `undefined -> "--"`.

### `test/e2e/helpers.ts` (mod)

Extend `openApp` (lines 14-17):
```ts
await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
await expect(page.getByTestId("cash-balance")).toContainText("$");
```
`apiTrade`, `uiTrade`, `heldQuantity` already exist and define the API contract (`POST /api/portfolio/trade` expects 200; `GET /api/portfolio` -> `positions[].ticker/quantity`).

## Shared Patterns

### DB access
**Source:** `backend/app/db.py:136-140, 168-174` -- connection-per-call, `closing(connect(db_path()))`, rows as `dict(r)`, `user_id = 'default'`, parameterized SQL.
**Apply to:** all of `portfolio.py`.

### Async/thread boundary
**Source:** `backend/app/api/watchlist.py:45-50` -- every sqlite call via `await asyncio.to_thread(fn, args)`.
**Apply to:** trade route, portfolio route, history route, reconcile_stream, snapshot loop.

### Router factory
**Source:** `watchlist.py:27-28`, `main.py:112-113` -- `create_x_router(cache, source)`, full `/api/...` paths.
**Apply to:** `api/portfolio.py`.

### Stream reconciliation
**Source:** `watchlist.py:52,62` (`source.add_ticker`/`remove_ticker`); `MarketDataSource` ABC in `market/interface.py` (add_ticker, remove_ticker, get_tickers). Only `reconcile_stream` may call `remove_ticker` after this phase.
**Apply to:** trade route (in `finally`), watchlist DELETE.

### Frontend fetch hook with stale guard
**Source:** `useWatchlist.ts:19-37`.
**Apply to:** `usePortfolio`, `PnlChart` history fetch.

### Clickable row/cell a11y
**Source:** `WatchlistRow.tsx:38-54` (`tabIndex=0`, Enter/Space, `aria-selected`, selected styling).
**Apply to:** positions rows, heatmap cells.

### Lint disable idiom
**Source:** `useWatchlist.ts:35`, `Terminal.tsx:22`: `// eslint-disable-next-line react-hooks/set-state-in-effect` before setState/fetch-in-effect.
**Apply to:** TradeBar ticker sync, PnlChart refetch effect.

### Money formatting
**Source:** `lib/format.ts` (`formatPrice`, `formatPct`); E2E parser strips all but `[0-9.-]` so test-id elements must contain only the formatted number.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/lib/treemap.ts` | utility | transform | No layout code exists; use RESEARCH Pattern 7 (verified squarify). Note UI-SPEC says `squarify(items, width, height)` returning `{id,x,y,w,h}`; RESEARCH uses `(items, box)`; planner picks one signature |
| Snapshot background task | service | event-driven | Only analog is `SimulatorDataSource._run_loop` (loop + per-iteration try/except); use RESEARCH Pattern 4 |
| ResizeObserver size hook | hook | event-driven | None in repo (AutoSize used by LW Charts only) |

## Notes for Planner

- Spec conflicts to resolve: P&L chart `data-testid="pnl-chart"` on inner wrapper (RESEARCH Pitfall 8) vs on panel (UI-SPEC says panel with canvas inside); both satisfy the E2E if `data-points` and the canvas are inside the same element, simplest is to keep `testId="pnl-chart"` on the Panel and set `data-points` through `Panel`'s `...rest` HTML attributes (Panel spreads `rest` onto `<section>`, Panel.tsx:17), avoiding a duplicate testid.
- Heatmap geometry: UI-SPEC says percent geometry in 0..100 space; RESEARCH says px from ResizeObserver. Pick one (px is needed for the label-hiding thresholds).
- avg_cost precision (4 dp, RESEARCH A1) and `openApp` helper change (A5) are flagged assumptions.

## Metadata

**Analog search scope:** `backend/app/**`, `backend/tests/**`, `frontend/src/**`, `test/e2e/helpers.ts`
**Files scanned:** ~45
**Pattern extraction date:** 2026-10-19
