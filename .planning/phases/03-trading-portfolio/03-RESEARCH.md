# Phase 3: Trading & Portfolio - Research

**Researched:** 2026-10-19
**Domain:** Python sqlite3 trade transactions + FastAPI portfolio API; React/Lightweight Charts v5 portfolio UI (treemap, P&L line, live header)
**Confidence:** HIGH (all patterns build on code already in the repo; sqlite/asyncio/treemap behaviours were run in this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Trade execution**
- Trading a ticker with no live price starts streaming it via `source.add_ticker` (simulator seeds instantly), then fills at the cache price. Needed for AI trades in Phase 4
- One SQLite transaction updates `users_profile.cash_balance`, upserts or deletes the `positions` row, and appends to `trades`; run via `asyncio.to_thread`. A module-level `asyncio.Lock` serializes trades. A portfolio snapshot is recorded right after each trade
- Quantity must be > 0 with at most 4 decimals (fractional shares). Cash and prices rounded to 2 dp. Average cost recomputed on buys (weighted); selling the full quantity deletes the position (epsilon 1e-9); avg cost unchanged on partial sells
- `POST /api/portfolio/trade {ticker, quantity, side}` (side `buy`|`sell`; ticker normalized like the watchlist: strip, uppercase, `^[A-Z]{1,5}$`, strings only) returns 200 `{trade, cash_balance, position}` (position null when sold out). Business-rule failures return 400 with a clear `detail`, e.g. "Insufficient cash: need $X, have $Y" or "Cannot sell N AAPL; you hold M". Invalid input returns 422. No state change on any failure

**Portfolio and snapshots**
- `GET /api/portfolio` returns `{cash_balance, total_value, unrealized_pnl, positions: [{ticker, quantity, avg_cost, current_price, market_value, unrealized_pnl, pnl_pct}]}`; `current_price` falls back to `avg_cost` when the cache has no price
- Snapshots: background task every 30 s, one after each trade, one at startup. `GET /api/portfolio/history` returns the last 500 snapshots oldest-first as `{total_value, recorded_at}` (bounded, PORT-08)
- Streamed set = watchlist ∪ held positions. Removing a ticker from the watchlist keeps streaming it while held; selling out a ticker that is not on the watchlist stops streaming it (prior-build bug)
- Header cash comes from `/api/portfolio` (load + after each trade); header total value updates live on each tick as cash + Σ quantity × live SSE price (fallback avg cost)

**Trading and portfolio UI**
- Trade bar below the main chart: `trade-ticker` input (prefilled with the selected ticker, uppercased), `trade-quantity` input, `buy-button` solid purple `#753991`, `sell-button` purple outline; `trade-error` inline in a fixed slot; fields keep ticker and clear quantity on success; no confirmation dialog
- Heatmap: hand-built squarified treemap of divs (no new dependency), sized by market value, colored by P&L % (green profit, red loss, intensity by magnitude; flat neutral), labels ticker and P&L %; `heatmap` container, `heatmap-cell-{TICKER}` with `data-pnl` = positive|negative|flat; empty state when no positions
- P&L chart: Lightweight Charts line series of total value from `/api/portfolio/history`, refetched after trades and every 30 s; `pnl-chart` with `data-points` = number of points; contains the chart canvas
- Positions table: `position-row-{TICKER}` rows with ticker, quantity, avg cost, current price (live from SSE), unrealized P&L, % change; clicking a row selects the ticker in the main chart; empty state when no positions
- Header: `total-value` and `cash-balance` show formatted dollars (E2E reads them with a numeric parser; initial values $10,000.00)
- Fold in Phase 2 UI-audit fixes: accent underline on the active panel title (Watchlist and Main chart, per UI-SPEC), and refocus the add input after a failed add
- Narrow-width layout stays in Phase 6 (UI-13)

### Claude's Discretion
- Backend module split (`app/portfolio/` vs single module), snapshot task placement, treemap algorithm details, exact positions table column widths within UI-SPEC tokens

### Deferred Ideas (OUT OF SCOPE)
- Narrow/tablet layout (Phase 6, UI-13)
- Snapshot row pruning beyond the bounded read (not needed for v1)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PORT-01 | GET /api/portfolio | `portfolio_view()` shared with snapshot task; cache fallback to avg_cost (Pattern 3) |
| PORT-02 | Buy via POST trade, instant fill, no fees | `execute_trade` single BEGIN IMMEDIATE transaction (Pattern 1) |
| PORT-03 | Sell; full sell removes position | Epsilon delete + 4dp re-rounding (Trade math) |
| PORT-04 | Fractional qty; weighted avg cost | Quantize to 4dp with noise tolerance (Pitfall 1) |
| PORT-05 | Reject insufficient cash/oversell, no state change | Validate inside the transaction; raise before any write (Pattern 1) |
| PORT-06 | Trades appended to log | INSERT in same transaction |
| PORT-07 | Snapshot every 30 s and after each trade (+ startup) | Lifespan task + `record_snapshot` (Pattern 4) |
| PORT-08 | Bounded history | `ORDER BY rowid DESC LIMIT 500` then reverse (Pattern 3) |
| UI-02 | Header live total, cash, dot | `derivePositions` + `usePortfolio` (Pattern 6) |
| UI-07 | Trade bar | TradeBar component, pending/err slot (Pitfall 7) |
| UI-08 | Positions table | Live price from SSE quotes (Pattern 6) |
| UI-09 | Treemap heatmap | Squarify function, verified (Pattern 7) |
| UI-10 | P&L chart | LW v5 LineSeries, dedupe seconds (Pattern 8, Pitfall 3) |
| UI-12 | Refresh after trades | `usePortfolio.refresh()` + version counter, reusable by Phase 4 chat |
| TEST-02 | pytest portfolio logic | Validation Architecture table |
</phase_requirements>

## Summary

Everything this phase needs is already in the repo: connection-per-call sqlite with `asyncio.to_thread` (`backend/app/db.py`), router factories taking `(cache, source)` (`api/watchlist.py`), a lifespan that starts the simulator, a lifespan-driven pytest `client` fixture, Lightweight Charts v5.2.1 with `chart.addSeries(XSeries, ...)`, and an SSE hook exposing `quotes`. No new dependency is needed on either side (squarified treemap is ~40 lines; verified here against the Bruls et al. worked example, areas preserved exactly).

The risk is not libraries but a handful of precise traps, all reproduced or reasoned in this session: (1) float noise in E2E quantities such as `held - 1` (1.2999999999999998) breaks a naive "max 4 decimals" check and the "sell all" comparison; (2) a module-level `asyncio.Lock` raises `RuntimeError: bound to a different event loop` on the second pytest loop once it has been contended; (3) Lightweight Charts throws on duplicate or non-ascending times and a trade snapshot can share a second with the 30 s snapshot; (4) E2E `readNumber(cash)` right after `openApp` reads `--` (NaN) unless the helper waits for the portfolio load; (5) a trade that auto-starts streaming a non-watched ticker and then fails validation must stop streaming it again.

**Primary recommendation:** Put all money logic in a new `backend/app/portfolio.py` (pure sync functions on a connection + thin async wrappers), make `reconcile_stream(ticker)` the only place that decides add/remove on the market source, create the trade lock inside the lifespan, and on the frontend compute header/table/heatmap from one pure `derivePositions(portfolio, quotes)`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Trade validation and atomic state change | API / Backend (sqlite txn) | — | Single source of truth for cash/positions; UI only displays errors |
| Fill price | API / Backend (price cache) | — | Server fills at cache price, client never sends price |
| Streamed set (watchlist ∪ positions) | API / Backend | — | Decides what the source produces; SSE carries whatever the cache holds |
| Portfolio snapshots | API / Backend (lifespan task) | Database | Must run with no browser open (PORT-07) |
| Live header total / row P&L | Browser | API (initial qty, avg cost, cash) | Recomputed every SSE tick from cash + Σ q × quote; server values are stale between fetches |
| Treemap layout | Browser | — | Pure function of positions + container size |
| P&L chart series | Browser | API (history) | Server supplies bounded history; client dedupes to seconds |

## Standard Stack

### Core (no additions)
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| sqlite3 (stdlib, SQLite 3.46.1 on Python 3.14.4) | stdlib | Trade transaction | Already the repo pattern [VERIFIED: ran in WSL] |
| FastAPI + pydantic | fastapi>=0.146 | Routes, 422 validation | Existing; `AddTicker` validator pattern [VERIFIED: backend/pyproject.toml] |
| lightweight-charts | 5.2.1 | P&L line series | Already installed; `npm view` returns 5.2.1 [VERIFIED: npm registry] |
| React 19.3.1 / Next 16.4.2 / Tailwind 4 | existing | UI | [VERIFIED: frontend/package.json] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-built squarify | d3-hierarchy / recharts Treemap | New dependency; CONTEXT locks hand-built |
| `Decimal` for money | float + round | Spec stores REAL columns and rounds to 2 dp; float + round at each boundary is sufficient (below) |

**Installation:** none. **Package Legitimacy Audit:** no new external packages; nothing to audit (slopcheck not needed).

## Architecture Patterns

### System Architecture Diagram

```
Browser                                  FastAPI (single process)
 TradeBar --POST /api/portfolio/trade--> trade route
                                           |  422 (pydantic)
                                           v
                                    source.add_ticker (if no cache price)
                                           |
                                    async with trade_lock
                                           |  price = cache.get(t)  (400 if none)
                                           v
                                    to_thread(execute_trade)  -- BEGIN IMMEDIATE
                                           |   read cash+position -> validate (TradeError -> 400)
                                           |   UPDATE cash / UPSERT|DELETE position / INSERT trade
                                           |   COMMIT
                                           v
                                    reconcile_stream(ticker)  (add or remove on source)
                                    to_thread(record_snapshot) (cash + sum q*price)
                                           v
                          <-- 200 {trade, cash_balance, position}
 usePortfolio.refresh() --GET /api/portfolio--> portfolio_view (DB read + cache prices)
 PnlChart --GET /api/portfolio/history--------> last 500 snapshots, oldest first
 usePriceStream <--SSE /api/stream/prices----- cache (watchlist ∪ held tickers)

Lifespan: init_db -> tickers = watchlist ∪ positions -> source.start -> startup snapshot
          -> create trade_lock + snapshot_loop task (sleep 30; snapshot)
 Shutdown: cancel snapshot task (await, suppress CancelledError) -> source.stop
Watchlist DELETE -> db.remove_ticker -> reconcile_stream (keeps streaming while held)
```

### Recommended Project Structure
```
backend/app/
├── portfolio.py          # TradeError, execute_trade, portfolio_view, record_snapshot, history, held_tickers
├── api/portfolio.py      # create_portfolio_router(cache, source, trade_lock getter)
├── streaming.py          # reconcile_stream(source, ticker) (or inside portfolio.py)
frontend/src/
├── lib/usePortfolio.ts   # fetch, trade(), version counter
├── lib/portfolio.ts      # derivePositions(), pnlState(), toSeries() (pure)
├── lib/treemap.ts        # squarify() (pure)
└── components/TradeBar.tsx, PositionsTable.tsx, Heatmap.tsx, PnlChart.tsx
```
Keep `db.py` for watchlist; put trade SQL in `portfolio.py` using `db.connect/db_path` (short modules per CLAUDE.md).

### Pattern 1: Atomic trade, connection-per-call, BEGIN IMMEDIATE
**What:** One sync function, run via `to_thread`, that opens its own connection, takes the write lock up front, validates, writes, commits. Python 3.14 default (`isolation_level=""`, legacy transaction control, `autocommit == -1`) accepts an explicit `BEGIN IMMEDIATE`: `in_transaction` becomes True and no implicit BEGIN is issued [VERIFIED: ran on 3.14.4].
**Why IMMEDIATE:** a deferred transaction that reads then writes fails *immediately* with SQLITE_BUSY ("database is locked", busy timeout not honoured) if another connection (snapshot task, watchlist add) wrote in between; IMMEDIATE takes the write lock at start and waits up to the 5 s default timeout instead [CITED: sqlite.org/lang_transaction.html]. It also protects when the HTTP request is cancelled while the thread keeps running (the asyncio lock is released but the thread is still committing). Keep the asyncio.Lock (locked decision), but BEGIN IMMEDIATE is what guarantees correctness.
```python
class TradeError(Exception):
    """Business-rule failure; message becomes the 400 detail."""

QTY_STEP = 4

def execute_trade(ticker: str, side: str, qty: float, price: float) -> dict:
    now = datetime.now(UTC).isoformat()
    with closing(connect(db_path())) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            cash = conn.execute("SELECT cash_balance FROM users_profile WHERE id='default'").fetchone()[0]
            pos = conn.execute("SELECT id, quantity, avg_cost FROM positions WHERE user_id='default' AND ticker=?", (ticker,)).fetchone()
            held = pos["quantity"] if pos else 0.0
            amount = round(qty * price, 2)
            if side == "buy":
                if amount > cash + 1e-9:
                    raise TradeError(f"Insufficient cash: need ${amount:,.2f}, have ${cash:,.2f}")
                new_cash = round(cash - amount, 2)
                new_qty = round(held + qty, 4)
                avg = round((held * pos["avg_cost"] + qty * price) / new_qty, 4) if pos else price
            else:
                if qty > held + 1e-9:
                    raise TradeError(f"Cannot sell {qty:g} {ticker}; you hold {held:g}")
                new_cash = round(cash + amount, 2)
                new_qty = round(held - qty, 4)
                avg = pos["avg_cost"] if pos else price
            # write: UPDATE cash; if new_qty <= 1e-9 DELETE position else UPSERT; INSERT trade
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
```
(Raising before any write already leaves no state change; the rollback is for unexpected errors. Per CLAUDE.md keep it this simple, no extra defensive layers.) Upsert: `INSERT ... ON CONFLICT(user_id, ticker) DO UPDATE SET quantity=excluded.quantity, avg_cost=excluded.avg_cost, updated_at=excluded.updated_at` [ASSUMED: standard SQLite 3.24+ syntax; SQLite here is 3.46.1].
Return `{trade: {id,ticker,side,quantity,price,executed_at}, cash_balance, position|None}`.

### Trade math (prescriptive)
- **Quantity validation (pydantic, 422):** `float`, reject bool (`StrictFloat`-style: accept int/float JSON, reject strings and bools), `allow_inf_nan=False`, `gt=0`, upper cap (recommend `le=1_000_000`, Claude's discretion). "At most 4 dp" check must tolerate IEEE noise: `abs(q*1e4 - round(q*1e4)) < 1e-6`, then **store `q = round(q, 4)`**. Measured: `2.3 - 1 = 1.2999999999999998` -> noise 1.8e-12, `round(.,4)=1.3` [VERIFIED: ran]. A strict `Decimal(str(q)).as_tuple().exponent >= -4` check would reject exactly the E2E `held - 1` quantity.
- **Cash:** `amount = round(qty*price, 2)`; `new_cash = round(cash ± amount, 2)`. Price is already 2 dp from `PriceCache.update`. Buy check `amount > cash + 1e-9`. Round half-even on 2.675 -> 2.67 is a float artefact [VERIFIED]; accept (consistent for buy and sell).
- **Position quantity drift:** re-round every stored quantity to 4 dp (`round(held ± qty, 4)`); then "sell all" is `new_qty <= 1e-9` and the E2E `sell held-1` then `sell remainder` hits exactly 0 after rounding. Oversell check `qty > held + 1e-9`.
- **Avg cost:** weighted on buys only. Recommend storing 4 dp (not 2) so unrealized P&L is not skewed by cent rounding on fractional lots (CONTEXT says "prices rounded to 2 dp" -- fill prices and cash; avg_cost precision is Claude's discretion; tests assert with `pytest.approx`). Partial sell leaves avg_cost untouched. Re-buying after a full sell starts fresh (row was deleted).
- **Display:** server `pnl_pct = (price-avg)/avg*100`, `unrealized_pnl = round((price-avg)*q, 2)`, `market_value = round(q*price, 2)`, `total_value = round(cash + Σ market_value, 2)` so shown numbers add up.

### Pattern 2: Lock created per lifespan, not at import
**Verified:** a module-level `asyncio.Lock()` contended in one `asyncio.run` then used in another raises `RuntimeError ... is bound to a different event loop` [VERIFIED: ran on 3.14.4]. pytest-asyncio here uses a function-scoped loop and `main.app` is imported once, so a concurrency test (`asyncio.gather` of two buys) would poison later tests. Create it in the lifespan: `app.state.trade_lock = asyncio.Lock()` (router reads `request.app.state.trade_lock`), or a module global `trade_lock` reassigned by `portfolio.reset_lock()` at lifespan start. Hold the lock around price read + `to_thread(execute_trade)` only; call `reconcile_stream` and snapshot after release (reconcile inside the lock is fine too but never call anything that re-acquires it).

### Pattern 3: portfolio_view and history
- `portfolio_view(cache)` (sync, called via `to_thread`): read cash + positions from DB, prices from `cache.get(t)` (thread-safe, `threading.Lock`), fallback `avg_cost`. Used by `GET /api/portfolio`, `record_snapshot` and the trade snapshot. Order positions by `rowid` for stable table order.
- History: `SELECT total_value, recorded_at FROM portfolio_snapshots WHERE user_id='default' ORDER BY rowid DESC LIMIT 500` then reverse in Python. Use rowid (insertion order), not `recorded_at`: `isoformat()` omits the fraction when microsecond == 0, so string order is not guaranteed to equal time order in general. Table PK is TEXT so `rowid` exists.

### Pattern 4: Snapshot task lifecycle (lifespan)
```python
@asynccontextmanager
async def lifespan(app):
    end_streams_on_exit_signal()
    await asyncio.to_thread(db.init_db)
    portfolio.reset_lock()                       # or app.state.trade_lock = asyncio.Lock()
    tickers = await asyncio.to_thread(portfolio.streamed_tickers)   # watchlist ∪ positions, ordered, deduped
    await source.start(tickers)
    await asyncio.to_thread(portfolio.record_snapshot, cache)      # startup snapshot, prices are seeded
    task = asyncio.create_task(portfolio.snapshot_loop(cache), name="snapshot-loop")
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    await source.stop()
```
`snapshot_loop`: `while True: await asyncio.sleep(30); try: await to_thread(record_snapshot, cache) except Exception: logger.exception(...)` (same shape as `SimulatorDataSource._run_loop`). Sleep first, since the startup snapshot was just taken. The existing `shutdown` Event only ends SSE generators; the snapshot task is cancelled in the lifespan teardown after uvicorn has closed connections, so no interaction. A failed insert must not kill the loop (per-iteration try/except is the one justified catch). Make the interval a parameter (`interval=30`) so a test can run it at 0.05 s.
Note for tests: every `client` fixture start writes one startup snapshot, so history tests expect >= 1 row, never 0.

### Pattern 5: Streamed set = watchlist ∪ positions
One function owns the decision, called from three places:
```python
async def reconcile_stream(source, ticker: str) -> None:
    """Stream the ticker iff it is on the watchlist or held."""
    keep = await asyncio.to_thread(db_is_watched_or_held, ticker)   # one connection, two EXISTS
    await (source.add_ticker if keep else source.remove_ticker)(ticker)
```
- **Startup:** `streamed_tickers()` = watchlist order, then held tickers not already present.
- **Trade route:** `if cache.get(t) is None: await source.add_ticker(t)` before the lock; **in a `finally` after the trade (success or `TradeError`)** call `reconcile_stream(t)`. The failure case matters: buying an unwatched ticker with insufficient cash must not leave it streaming. Sell-out of an unwatched ticker then stops streaming (prior-build bug).
- **Watchlist DELETE:** replace the unconditional `source.remove_ticker` with `reconcile_stream`. Watchlist ADD of a held ticker: `source.add_ticker` is already idempotent (`if ticker in self._sim.tickers: return`) [VERIFIED: simulator_source.py].
- `SimulatorDataSource.add_ticker` on an unknown symbol seeds a price immediately and writes the cache (existing watchlist PYPL test proves `cache.get("PYPL")` is non-None), so "fill at cache price" works for any `[A-Z]{1,5}` with the simulator. If the cache still has no price afterwards (Massive, Phase 5) return 400 "No price available for X".
- Tiny race (watchlist add vs sell-out reconcile): each reconcile re-reads DB truth in one call, so the last writer converges; no extra lock needed.
- `source.remove_ticker` calls `self._sim.remove_ticker` which is a no-op for absent tickers, but verify it does not raise for a ticker never added (it does `ticker not in self._prices` guard) [VERIFIED: simulator.py:68].

### Pattern 6: Frontend portfolio state and derived rows
`usePortfolio()` mirrors `useWatchlist` (the `seq` ref ignores stale responses): `{portfolio, loading, error, version, refresh, trade}`; `trade(ticker, qty, side)` POSTs, returns `string | null` (error text from `detail` on 400, fixed copy on 422/network), then `await refresh()` and `setVersion(v => v+1)`. `version` drives the PnlChart refetch and is what Phase 4 bumps after AI trades (UI-12) -- expose `refresh` for the chat panel.
```ts
export function derivePositions(p: Portfolio | null, quotes: Record<string, Quote>) {
  const rows = (p?.positions ?? []).map((x) => {
    const price = quotes[x.ticker]?.price ?? x.avg_cost;
    const value = x.quantity * price;
    const pnl = (price - x.avg_cost) * x.quantity;
    return { ...x, current_price: price, market_value: value, unrealized_pnl: pnl, pnl_pct: ((price - x.avg_cost) / x.avg_cost) * 100 };
  });
  const total = p ? p.cash_balance + rows.reduce((s, r) => s + r.market_value, 0) : undefined;
  return { rows, total };
}
```
Header: `total-value` = `formatPrice(total)`, `cash-balance` = `formatPrice(p?.cash_balance)` (existing `formatPrice` returns `--` for undefined). Header becomes a client component taking props (currently static, no "use client" needed because Terminal is). `useMemo` on `[portfolio, quotes]`; SSE fires every 500 ms so this is cheap for ~10 rows. "flat" for P&L state: use the same rule as `formatPct`: `Number(Math.abs(pct).toFixed(2)) === 0` so a cell never says "0.00%" while colored green.

### Pattern 7: Squarified treemap (verified)
Bruls, Huizing, van Wijk, "Squarified Treemaps" (2000): sort values descending; scale to the box area; lay out rows along the *shorter* side; add an item to the current row while `worst()` does not increase.
```ts
export type Box = { x: number; y: number; w: number; h: number };
const worst = (row: number[], side: number) => {
  const s = row.reduce((a, b) => a + b, 0);
  return Math.max((side * side * Math.max(...row)) / (s * s), (s * s) / (side * side * Math.min(...row)));
};
/** items need value > 0; returns one Box per item in descending-value order. */
export function squarify<T extends { value: number }>(items: T[], box: Box): (T & Box)[] {
  const sorted = items.filter((i) => i.value > 0).sort((a, b) => b.value - a.value);
  const total = sorted.reduce((s, i) => s + i.value, 0);
  if (total === 0) return [];
  const k = (box.w * box.h) / total;
  const out: (T & Box)[] = [];
  let { x, y, w, h } = box, i = 0;
  while (i < sorted.length) {
    const side = Math.min(w, h);
    const row = [sorted[i].value * k];
    let j = i + 1;
    while (j < sorted.length && worst([...row, sorted[j].value * k], side) <= worst(row, side)) row.push(sorted[j++].value * k);
    const s = row.reduce((a, b) => a + b, 0);
    if (w >= h) { const cw = s / h; let yy = y; row.forEach((a, n) => { out.push({ ...sorted[i + n], x, y: yy, w: cw, h: a / cw }); yy += a / cw; }); x += cw; w -= cw; }
    else { const rh = s / w; let xx = x; row.forEach((a, n) => { out.push({ ...sorted[i + n], x: xx, y, w: a / rh, h: rh }); xx += a / rh; }); y += rh; h -= rh; }
    i = j;
  }
  return out;
}
```
This is a direct port of the Python version I ran: values `[6,6,4,3,2,2,1]` in a 6x4 box reproduce the paper's example layout (first column two 3x2 cells; areas sum to 24 exactly) [VERIFIED: ran Python equivalent]. Run `npm run typecheck` on the TS port; strict mode complains about nothing here other than the destructuring `let` which is fine.
**Rendering:** measure the container with a small `ResizeObserver` hook (`{w,h}` state) so rows are squarified for the real aspect ratio, then render `position:absolute; left/top/width/height` in px (or `%` of w/h) with `box-border border border-bg` for 1 px gutters; `overflow-hidden`; show the pct label only when `w > 48 && h > 28` (otherwise only a `title` tooltip). Cells must still have a non-zero box so Playwright `toBeVisible()` passes for a tiny position (a 1-share NVDA next to larger positions is >= several px in a ~400x250 panel). Render the `heatmap` container always (empty-state text inside) so `getByTestId("heatmap")` is visible even with no positions; `Panel testId="heatmap"` already provides that and is the container.
**Color:** intensity `i = min(|pct| / 10, 1)`; positive `rgba(63,185,80, 0.18 + 0.52*i)`, negative `rgba(248,81,73, ...)` (tokens `--color-up #3fb950`, `--color-down #f85149`), flat `var(--color-surface)`. `data-pnl` from the same flat rule as above.

### Pattern 8: P&L chart (Lightweight Charts v5)
Mirror `MainChart` (create once, cleanup resets refs): `import { LineSeries, createChart } from "lightweight-charts"; chart.addSeries(LineSeries, { color: "#209dd7", lineWidth: 2 })` [VERIFIED: v5.2.1 installed; repo already uses `addSeries(AreaSeries, ...)`]. Reuse `clock()`/price formatter options (extract `createChart` base options from `createAreaChart` rather than duplicating). Data: `setData` on each fetch (<= 500 points, no need for incremental `update`), then `fitContent()` on first data only.
```ts
/** ISO strings oldest-first -> strictly ascending whole seconds; last value wins per second. */
export function toSeries(h: { total_value: number; recorded_at: string }[]) {
  const out: { time: UTCTimestamp; value: number }[] = [];
  for (const s of h) {
    const time = Math.floor(Date.parse(s.recorded_at) / 1000) as UTCTimestamp;
    const last = out[out.length - 1];
    if (last && time < last.time) continue;
    if (last && time === last.time) last.value = s.total_value; else out.push({ time, value: s.total_value });
  }
  return out;
}
```
Backend writes `datetime.now(UTC).isoformat()` -> `...+00:00`, parsed correctly by `Date.parse`. `data-points={series.length}` goes on the element that wraps the canvas host (put `data-testid="pnl-chart"` on that inner div, not on `Panel`, to avoid a duplicate testid; remove `testId="pnl-chart"` from the Panel). Show an overlay "Collecting portfolio history..." when < 2 points (like `main-chart-empty`) but keep the chart host mounted so `canvas` exists (E2E needs `canvas` visible). Refetch triggers: mount, `version` change (trade), `setInterval(30_000)`; guard stale responses with a seq ref as in `useWatchlist`. Tip: live-update the last point with header total? Not required; keep chart = server snapshots only.

### Anti-Patterns to Avoid
- Reading the price inside the thread from `main.cache` global: pass price as an argument (testable, no import cycles).
- Computing total in the snapshot task from the *client*: it must use `portfolio_view(cache)` server side.
- Making the header wait for the 30 s refetch: header total is derived per SSE tick.
- `ORDER BY recorded_at` for bounded history (see Pattern 3).
- Calling `source.remove_ticker` directly from routes anywhere except via `reconcile_stream`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic multi-table update | manual compensating writes | one `BEGIN IMMEDIATE ... COMMIT` | partial failure leaves cash/position inconsistent |
| Upsert | SELECT-then-INSERT/UPDATE branches | `INSERT ... ON CONFLICT DO UPDATE` | UNIQUE (user_id, ticker) already exists |
| Input validation | manual body parsing | pydantic validators (reuse `AddTicker` normalizer; extract a shared `Ticker` annotated type) | consistent 422 |
| Time-series charting | custom canvas | Lightweight Charts LineSeries | already a dependency |
| Treemap | d3/recharts | the 40-line `squarify` (locked: no new dependency) | — |
| Currency/pct formatting | new helpers | extend `lib/format.ts` (`formatPrice`, `formatPct`; add `formatQty`) | consistent with E2E numeric parser |

## Common Pitfalls

### Pitfall 1: Float noise in quantities breaks the 4 dp rule and sell-all
**What goes wrong:** E2E sends `held - 1` (e.g. `1.2999999999999998`); strict decimal-place validation returns 422; or `held - qty` leaves `2.2e-16` so the position row is not deleted and `heldQuantity` is not exactly 0 (`expect(...).toBe(0)`).
**How to avoid:** tolerance check + `round(q,4)` at the boundary; re-round stored quantity; delete when `<= 1e-9`.
**Warning signs:** 03 sell test fails with 422 or a ghost `position-row-MSFT`.

### Pitfall 2: Module-level asyncio.Lock across pytest loops
See Pattern 2. [VERIFIED: ran.] Warning sign: `RuntimeError: ... is bound to a different event loop` only in later tests after adding a `gather` concurrency test.

### Pitfall 3: Duplicate/non-ascending times crash Lightweight Charts
Trade snapshot + 30 s snapshot or two quick trades in the same second give equal `floor(seconds)`. `setData` throws (`data must be asc ordered by time`) and the whole chart goes blank. Use `toSeries` (dedupe). Same-second pairs are *likely* in E2E (`apiTrade` then page load) [CITED: tradingview.github.io/lightweight-charts docs, "time must be unique and ascending" -- already encoded in `appendPoint` in usePriceStream.ts].

### Pitfall 4: E2E reads `--` before the portfolio loads
`openApp` only waits for SSE `connected`. `readNumber(cash)` on `--` gives NaN (`Number("-")`), so 03's `before` is NaN and `toBeLessThan(NaN)` fails. **Mitigation (both):** extend `helpers.openApp` to also `await expect(page.getByTestId("cash-balance")).toContainText("$")`; and have the UI not clear previously-loaded values on refetch. The helper edit is a test-infra change the plan must include (File: `test/e2e/helpers.ts`).

### Pitfall 5: Non-watched ticker left streaming after a failed trade
Auto `add_ticker` before the trade, then `TradeError`. Fix: `reconcile_stream` in `finally`. Test: buy unwatched `ZZZZ` with insufficient cash, assert `"ZZZZ" not in source.get_tickers()` and `cache.get("ZZZZ") is None`.

### Pitfall 6: `database is locked` from deferred upgrade
Snapshot insert (task) racing a trade's read-then-write. Fixed by BEGIN IMMEDIATE (Pattern 1) and by keeping all connections short-lived with the default 5 s timeout. WAL is already enabled in `init_db`.

### Pitfall 7: `trade-error` visibility semantics
Playwright `toBeVisible()` passes for an empty element with a box, so a permanently rendered empty `data-testid="trade-error"` makes the oversell test pass vacuously, and it also makes "no error" tests wrong. Render the fixed-height slot wrapper always, but render the `trade-error` element (role="alert") only when there is a message; clear it on the next attempt/successful trade. Disable buy/sell while a request is pending (prevents double submit) and refocus the quantity input after success.

### Pitfall 8: Panel testId vs inner testids
`Panel` puts `data-testid` on the `<section>`. `heatmap` can stay there; `pnl-chart` needs `data-points` and must "contain the chart canvas" -- put it on the inner wrapper. Positions panel: keep a `positions` testid on Panel; rows `position-row-{TICKER}` with `onClick` select + keyboard (`tabIndex=0`, Enter) since rows are clickable.

### Pitfall 9: Header total flicker/NaN
`derivePositions` returns `total: undefined` until the first portfolio fetch; header shows `--`. Do not default to `0` (E2E 01 polls for exactly 10000, which is fine because it polls).

### Pitfall 10: Selected ticker after sell-out / watchlist removal
`Terminal` resets `selected` when it is not in watchlist `rows`. A position row click for a held-but-unwatched ticker would immediately be reset to `rows[0]`. Change the effect to keep selection valid against `watchlist ∪ positions`, and make MainChart data available: `usePriceStream` already keeps `chart[ticker]` for any ticker in the SSE payload, which includes held ones. Plan this as an explicit small task.

## Code Examples

### Trade route sketch
```python
class TradeRequest(BaseModel):
    ticker: Ticker           # shared annotated normalizer (strip/upper/regex, strings only)
    side: Literal["buy", "sell"]
    quantity: Qty            # float, gt=0, allow_inf_nan=False, 4 dp with tolerance -> round(.,4)

@router.post("/api/portfolio/trade")
async def trade(body: TradeRequest, request: Request) -> dict:
    if cache.get(body.ticker) is None:
        await source.add_ticker(body.ticker)
    try:
        async with request.app.state.trade_lock:
            update = cache.get(body.ticker)
            if update is None:
                raise HTTPException(400, f"No price available for {body.ticker}")
            result = await asyncio.to_thread(portfolio.execute_trade, body.ticker, body.side, body.quantity, update.price)
    except TradeError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        await reconcile_stream(source, body.ticker)
    await asyncio.to_thread(portfolio.record_snapshot, cache)
    return result
```
Note `bool` is an `int` subclass in pydantic's lax float mode: add `strict=True` semantics for bool (existing watchlist test rejects `True`/`False`/`123` for ticker; mirror with a quantity test for `true`, `"5"`, `0`, `-1`, `1.00001`, `NaN`).

### Querying the history cap
`SELECT total_value, recorded_at FROM (SELECT rowid AS r, * FROM portfolio_snapshots WHERE user_id='default' ORDER BY rowid DESC LIMIT 500) ORDER BY r`

## Runtime State Inventory
Not a rename/refactor phase. Existing-state note only: tables `positions`, `trades`, `portfolio_snapshots` already exist in `backend/db/schema.sql` (no schema change, no migration). Existing dev DBs from Phase 2 have empty trade tables and `cash_balance 10000`; the user's old container on :8000 has its own volume and must not be touched.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv / Python | backend tests, server | yes | Python 3.14.4, SQLite 3.46.1 (`~/.local/bin/uv`) | — |
| node/npm/npx (Windows wrappers) | lint, typecheck, build, Playwright | yes (used in Phase 2) | npm registry shows lightweight-charts 5.2.1 | — |
| Playwright + chromium | E2E 01/03/04 | yes (Phase 2 ran 02/06) | per `test/package.json` | — |
| Ports 8010+ | verification | free by convention | host 8000 is the user's container | pick 8014+ (8011-8013 used by Phase 2) |

No missing dependencies.

## State of the Art

| Old | Current | Impact |
|-----|---------|--------|
| LW charts v4 `chart.addLineSeries()` | v5 `chart.addSeries(LineSeries, opts)` | use the v5 form already in `MainChart.tsx` |
| sqlite3 `isolation_level` legacy | 3.12+ `autocommit` attribute exists; default remains legacy | keep default + explicit `BEGIN IMMEDIATE`; do not mix with `autocommit=False` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Store avg_cost at 4 dp instead of 2 dp | Trade math | Hidden test expecting 2 dp avg; low (tests use approx; round-number cases identical) |
| A2 | Cap quantity at 1,000,000 | Trade math | Arbitrary; harmless, discretionary |
| A3 | `INSERT ... ON CONFLICT DO UPDATE` upsert syntax | Pattern 1 | None (SQLite 3.46.1 supports it) but not independently re-run here |
| A4 | Intensity scale of 10% = full color | Pattern 7 | Visual only; UI-SPEC may override |
| A5 | Changing `helpers.openApp` to wait for cash is acceptable | Pitfall 4 | If E2E files are frozen, UI must guarantee cash text before connection dot turns green (hard) -- ask |

## Open Questions

1. **Sell price for the snapshot-after-trade inside or outside the txn?**
   - RESOLVED by CONTEXT: "A portfolio snapshot is recorded right after each trade." Separate call after commit; snapshot uses current cache prices.
2. **Trade lock scope vs reconcile**
   - RESOLVED: lock covers price read + DB thread only; reconcile and snapshot after release.
3. **Does `/api/portfolio` need `Cache-Control`?** Not needed; client fetches with the seq guard. RESOLVED (no).
4. **E2E helper change (A5)** -- planner should include it; confirm with user only if test files are considered frozen.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio 1.4 (asyncio_mode auto), httpx ASGITransport; Playwright for E2E |
| Config file | `backend/pyproject.toml`; `test/playwright.config.ts` |
| Quick run command | `cd backend && ~/.local/bin/uv run pytest tests/test_portfolio.py tests/test_portfolio_api.py -x -q` |
| Full suite command | `cd backend && ~/.local/bin/uv run pytest -q && cd ../frontend && npm run lint && npm run typecheck && npm run build` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PORT-01 | GET portfolio shape, fallback to avg_cost, total/pnl math | unit+api | `pytest tests/test_portfolio_api.py::test_get_portfolio -x` | Wave 0 |
| PORT-02 | buy fills at cache price, cash drops, 200 shape | api | `pytest tests/test_portfolio_api.py::test_buy` | Wave 0 |
| PORT-03 | partial sell keeps avg; full sell deletes row, position null | api | `pytest ...::test_sell_partial_and_all` | Wave 0 |
| PORT-04 | fractional qty, 4 dp tolerance (`1.2999999999999998` ok, `1.00001` 422), weighted avg | unit | `pytest tests/test_portfolio.py -k "avg or fractional"` | Wave 0 |
| PORT-05 | oversell / insufficient cash -> 400 with message, DB unchanged (cash, position, trades count); selling at a loss realises correct cash | unit+api | `pytest -k "oversell or insufficient or loss"` | Wave 0 |
| PORT-06 | trades row per success, none per failure | unit | `pytest -k trade_log` | Wave 0 |
| PORT-07 | snapshot after trade; startup snapshot; loop at 0.05 s interval writes rows; task cancelled on lifespan exit | api | `pytest tests/test_snapshots.py` | Wave 0 |
| PORT-08 | history <= 500 oldest-first (insert 600 rows) | unit | `pytest -k history_bounded` | Wave 0 |
| (streamed set) | held ticker stays after watchlist DELETE; sold-out unwatched stops; failed trade on unwatched stops; startup union | api | `pytest tests/test_streaming_union.py` | Wave 0 |
| (concurrency) | `gather` two buys that jointly exceed cash -> exactly one 200 | api | `pytest -k concurrent` | Wave 0 |
| TEST-02 | the above collectively | pytest | `pytest -q` | Wave 0 |
| UI-02/07/08/12 | cash/total shown, trade, row appears, error shown | e2e | `cd test && WSLENV=BASE_URL BASE_URL=http://localhost:8014 npx playwright test e2e/03-trading.spec.ts e2e/01-fresh-start.spec.ts` | exists |
| UI-09/10 | heatmap cell `data-pnl`, pnl-chart canvas + data-points | e2e | `... npx playwright test e2e/04-portfolio-viz.spec.ts` | exists |
| UI (all) | compile/lint | static | `cd frontend && npm run lint && npm run typecheck && npm run build` | exists |
| (smoke) | server API sanity | curl | start `DB_PATH=$D/p3.db STATIC_DIR=../frontend/out uv run uvicorn app.main:app --port 8014 --timeout-graceful-shutdown 2`, `curl -XPOST localhost:8014/api/portfolio/trade -H 'content-type: application/json' -d '{"ticker":"aapl","side":"buy","quantity":2}'` -> 200; `side:"x"` -> 422; sell 9999 -> 400; stop by recorded PID (`pkill -INT -P $PID; kill -INT $PID`, never `pkill -f uvicorn`) | — |

E2E run order matters: all specs share one DB and run alphabetically on a single worker: **run `01-fresh-start` first on a fresh `DB_PATH`** (it asserts cash and total exactly 10000; any prior trade breaks it), then 03, 04. Spec 05 (chat) is Phase 4; do not include. Re-running 03/04 on the same DB is safe (cumulative small buys, sell test self-provisions MSFT).

### Sampling Rate
- **Per task commit:** quick pytest for touched module; `npm run typecheck` for TS tasks
- **Per wave merge:** full pytest + lint + typecheck + build
- **Phase gate:** full suite green plus Playwright 01, 03, 04 (and 02, 06 regression) on a scratch server

### Wave 0 Gaps
- [ ] `backend/tests/test_portfolio.py` (unit: math, rounding, epsilon, lock/concurrency)
- [ ] `backend/tests/test_portfolio_api.py` (status codes, shapes, 422 matrix)
- [ ] `backend/tests/test_snapshots.py`, `test_streaming_union.py`
- [ ] A small `seed_position(...)` fixture helper in `conftest.py`; tests that need exact prices set them via `main.cache.update("AAPL", 100.0)` (the simulator ticks every 0.5 s, so for deterministic fills either call `await main.source.stop()` in the test or assert with the returned trade price rather than a constant)
- [ ] `test/e2e/helpers.ts` `openApp` waits for cash text (Pitfall 4)
- Frontend unit tests are Phase 6; for now `squarify` and `toSeries` correctness is gated by typecheck plus the E2E; optionally a throwaway node assertion run during execution.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2/V3 Auth/Session | no (single-user, no login by design) | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | pydantic: strict types, regex ticker, `Literal` side, finite positive bounded quantity |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| SQL injection via ticker | Tampering | parameterized `?` queries only; ticker regex before use |
| Float overflow/NaN/Inf quantity corrupting cash | Tampering | `allow_inf_nan=False`, upper bound, 4 dp quantization |
| Negative quantity to mint cash | Tampering | `gt=0` |
| Concurrent double-spend | Tampering | asyncio.Lock + BEGIN IMMEDIATE |
| Unbounded history response / table growth (DoS) | DoS | `LIMIT 500` on read (row pruning deferred by CONTEXT) |
| Arbitrary ticker triggers unbounded streaming growth | DoS | accepted (single-user local app); regex limits to 1-5 letters |

## Sources

### Primary (HIGH confidence)
- Repo code read in this session: `backend/app/{db,main}.py`, `api/{watchlist,stream}.py`, `market/{cache,simulator,simulator_source}.py`, `backend/db/schema.sql`, `backend/tests/conftest.py`, frontend `usePriceStream/useWatchlist/MainChart/Header/Terminal/Panel/format`, `test/e2e/{01,03,04,helpers}`, `playwright.config.ts`
- Executed in WSL on Python 3.14.4 / SQLite 3.46.1: BEGIN IMMEDIATE under default isolation, asyncio.Lock cross-loop RuntimeError, float noise table, squarify reproduction of the Bruls example
- `npm view lightweight-charts version` -> 5.2.1

### Secondary (MEDIUM)
- sqlite.org transaction docs (deferred -> write upgrade returns SQLITE_BUSY; IMMEDIATE takes lock at BEGIN) -- from training knowledge, consistent with SQLite behaviour, not re-fetched [ASSUMED-level for exact wording]
- Bruls/Huizing/van Wijk "Squarified Treemaps" (2000) -- algorithm matches the verified worked example

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new packages
- Architecture: HIGH -- reuses verified Phase 1/2 patterns
- Pitfalls: HIGH for 1, 2, 4 (reproduced/derived from the actual E2E specs); MEDIUM for SQLite BUSY wording

**Research date:** 2026-10-19
**Valid until:** 2026-11-18
