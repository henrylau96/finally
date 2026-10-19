# Phase 3: Trading & Portfolio - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning

<domain>
## Phase Boundary

User buys and sells shares at market and watches portfolio value, positions and P&L update live. Delivers: trade execution API with validation, portfolio API, portfolio snapshots (30s background task, after each trade, at startup) with bounded history, streamed set = watchlist ∪ held positions, and the UI: header live total value and cash, trade bar, positions table, treemap heatmap, P&L chart. Requirements: PORT-01..08, UI-02, UI-07..10, UI-12, TEST-02.

Not in this phase: chat (Phase 4), Massive (Phase 5), Docker/tablet/frontend unit tests (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Trade execution
- Trading a ticker with no live price starts streaming it via `source.add_ticker` (simulator seeds instantly), then fills at the cache price. Needed for AI trades in Phase 4
- One SQLite transaction updates `users_profile.cash_balance`, upserts or deletes the `positions` row, and appends to `trades`; run via `asyncio.to_thread`. A module-level `asyncio.Lock` serializes trades. A portfolio snapshot is recorded right after each trade
- Quantity must be > 0 with at most 4 decimals (fractional shares). Cash stored at full precision (moves by exactly quantity x price) and displayed/returned at 2 dp (revised by review fix CR-01). Average cost recomputed on buys (weighted); selling the full quantity deletes the position (epsilon 1e-9); avg cost unchanged on partial sells
- `POST /api/portfolio/trade {ticker, quantity, side}` (side `buy`|`sell`; ticker normalized like the watchlist: strip, uppercase, `^[A-Z]{1,5}$`, strings only) returns 200 `{trade, cash_balance, position}` (position null when sold out). Business-rule failures return 400 with a clear `detail`, e.g. "Insufficient cash: need $X, have $Y" or "Cannot sell N AAPL; you hold M". Invalid input returns 422. No state change on any failure

### Portfolio and snapshots
- `GET /api/portfolio` returns `{cash_balance, total_value, unrealized_pnl, positions: [{ticker, quantity, avg_cost, current_price, market_value, unrealized_pnl, pnl_pct}]}`; `current_price` falls back to `avg_cost` when the cache has no price
- Snapshots: background task every 30 s, one after each trade, one at startup. `GET /api/portfolio/history` returns the last 500 snapshots oldest-first as `{total_value, recorded_at}` (bounded, PORT-08)
- Streamed set = watchlist ∪ held positions. Removing a ticker from the watchlist keeps streaming it while held; selling out a ticker that is not on the watchlist stops streaming it (prior-build bug)
- Header cash comes from `/api/portfolio` (load + after each trade); header total value updates live on each tick as cash + Σ quantity × live SSE price (fallback avg cost)

### Trading and portfolio UI
- Trade bar below the main chart: `trade-ticker` input (prefilled with the selected ticker, uppercased), `trade-quantity` input, `buy-button` solid purple `#753991`, `sell-button` purple outline; `trade-error` inline in a fixed slot; fields keep ticker and clear quantity on success; no confirmation dialog
- Heatmap: hand-built squarified treemap of divs (no new dependency), sized by market value, colored by P&L % (green profit, red loss, intensity by magnitude; flat neutral), labels ticker and P&L %; `heatmap` container, `heatmap-cell-{TICKER}` with `data-pnl` = positive|negative|flat; empty state when no positions
- P&L chart: Lightweight Charts line series of total value from `/api/portfolio/history`, refetched after trades and every 30 s; `pnl-chart` with `data-points` = number of points; contains the chart canvas
- Positions table: `position-row-{TICKER}` rows with ticker, quantity, avg cost, current price (live from SSE), unrealized P&L, % change; clicking a row selects the ticker in the main chart; empty state when no positions
- Header: `total-value` and `cash-balance` show formatted dollars (E2E reads them with a numeric parser; initial values $10,000.00)
- Fold in Phase 2 UI-audit fixes: accent underline on the active panel title (Watchlist and Main chart, per UI-SPEC), and refocus the add input after a failed add
- Narrow-width layout stays in Phase 6 (UI-13)

### Claude's Discretion
- Backend module split (`app/portfolio/` vs single module), snapshot task placement, treemap algorithm details, exact positions table column widths within UI-SPEC tokens

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/db.py` connection-per-call repository + `asyncio.to_thread`; `backend/db/schema.sql` already has positions, trades, portfolio_snapshots, users_profile (cash 10000 seeded)
- `backend/app/api/watchlist.py` router factory pattern and `AddTicker` validator (strings only, regex); `backend/app/main.py` lifespan (init_db, load tickers, source.start), module-level cache/source
- `backend/tests/conftest.py` lifespan + tmp DB fixture
- Frontend: `usePriceStream` (quotes, history, chart buffer), `useWatchlist`, `MainChart` (Lightweight Charts v5 patterns: create once, setData/update, cleanup resets refs), `Panel`, `Header`, `Terminal`, `format.ts`

### Established Patterns
- Router factories with full `/api/...` paths; 422 via pydantic; DB calls via to_thread; tests per endpoint with the lifespan fixture
- Verification on ports 8010+ with scratch DB_PATH; stop by explicit PID; `node`/`npm` are Windows wrappers (WSLENV for env vars)

### Integration Points
- `test/e2e/03-trading.spec.ts`, `04-portfolio-viz.spec.ts`, `01-fresh-start.spec.ts` (cash-balance and total-value = 10000), `helpers.ts` (`uiTrade`, `apiTrade`, `heldQuantity`)
- UI-SPEC from Phases 1 and 2 for tokens; `02-UI-REVIEW.md` for the folded fixes

</code_context>

<specifics>
## Specific Ideas

- Prior-build pitfalls: unbounded snapshot history; sold-out non-watchlist ticker kept streaming; blocking sqlite in async paths
- E2E sell test sells fractional remainder; quantities like `held - 1` must work

</specifics>

<deferred>
## Deferred Ideas

- Narrow/tablet layout (Phase 6, UI-13)
- Snapshot row pruning beyond the bounded read (not needed for v1)

</deferred>
