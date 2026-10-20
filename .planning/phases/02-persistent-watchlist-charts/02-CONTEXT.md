# Phase 2: Persistent Watchlist & Charts - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning

<domain>
## Phase Boundary

User manages a persistent watchlist and inspects any ticker in a larger chart. Delivers: SQLite database created and seeded at startup (all six PLAN.md tables, default user with $10,000 cash, 10 default tickers), watchlist REST API (`GET/POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`) that drives what the market source streams, watchlist add/remove UI, and a Lightweight Charts main chart for the selected ticker. Requirements: DATA-01, DATA-02, DATA-03, WATCH-01..04, UI-05, UI-06.

Not in this phase: trading, positions, portfolio numbers in the header (Phase 3), chat (Phase 4), Massive (Phase 5), Docker volume persistence and tablet layout (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Database layer
- Stdlib `sqlite3` with small repository functions; async routes call them via `asyncio.to_thread` so the event loop never blocks (prior-build pitfall)
- `DB_PATH` env var, default `<repo>/db/finally.db` (the Dockerfile already sets `DB_PATH=/app/db/finally.db`); create the parent dir if missing
- Initialize in the app lifespan at startup: execute `backend/db/schema.sql` (`CREATE TABLE IF NOT EXISTS`), then seed if `users_profile` is empty (PLAN.md section 4 puts schema/seed in `backend/db/`)
- Create all six PLAN.md tables now (users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages) with the PLAN.md columns; every table has `user_id` defaulting to `"default"`; UNIQUE (user_id, ticker) on watchlist and positions

### Watchlist API and streaming
- Ticker input is trimmed and uppercased, then must match `^[A-Z]{1,5}$`, else 422. On the simulator, unknown symbols get a 50-300 seed price (Phase 1 behavior)
- `GET /api/watchlist` returns a list of `{ticker, price, previous_price, direction, day_change_pct, added_at}`; price fields are null until the ticker has ticked
- `POST /api/watchlist {ticker}` returns 201 with the row; a duplicate returns 200 with the existing row (no error, no second row)
- `DELETE /api/watchlist/{ticker}` returns 204; 404 when not watched (E2E `ensureNotWatched` expects 204/404)
- Startup loads watchlist tickers from the DB into the market source (replacing hardcoded DEFAULT_TICKERS at runtime). Add/remove update DB, source (`add_ticker`/`remove_ticker`) and cache together, so a removed ticker stops streaming and stays removed after restart. Phase 3 will widen the streamed set to watchlist plus held positions
- Frontend watchlist rows come from `GET /api/watchlist` on load and after each add/remove, replacing the hardcoded `frontend/src/lib/tickers.ts` (fixes review WR-03); the SSE stream fills prices

### Watchlist UI and main chart
- Add control at the top of the watchlist panel: input `watchlist-add-input` and purple (`#753991`) "Add" button `watchlist-add-button`; Enter submits; input uppercased; invalid ticker or API error shown inline
- Remove: small × button per row (`watchlist-remove-{TICKER}`), visible on hover/focus, no confirmation
- Main chart: Lightweight Charts 5.2 area chart of the selected ticker's price since page load from a deeper client buffer (~1000 points, separate from the 120-point sparkline buffer); `main-chart` element carries `data-ticker` of the selection; default selection AAPL; clicking (or Enter/Space on) a row selects it (E2E `02-watchlist.spec.ts`)
- Fold in Phase 1 UI-review fixes touching these components: no layout shift when the "Waiting for prices" notice disappears (fixed-height slot), panel bodies use `--color-bg` per UI-SPEC 60/30/10 (surface for chrome), proper table roles (`row`/`cell`/`columnheader`) with `aria-selected` on the selected row, Space selects; "Reconnecting" notice takes precedence over "Waiting for prices"
- Tablet auto-collapse of the chat dock stays in Phase 6 (UI-13)

### Claude's Discretion
- Module split inside `backend/app/db/` vs `backend/db/`, router file names, frontend data-fetch helper shape, chart styling details within the UI-SPEC tokens

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/market/` (Phase 1): `MarketDataSource` with `start(tickers)`, `stop()`, `add_ticker`, `remove_ticker`, `get_tickers`; `PriceCache` with `get_all()`, `remove`, `version`, `PriceUpdate.to_dict()` (six keys); factory `create_market_data_source(cache)`
- `backend/app/main.py`: lifespan starts the source with `DEFAULT_TICKERS`, mounts static last; module-level `cache` and `source`; shutdown event for SSE
- `backend/app/api/health.py`, `stream.py` router patterns
- `frontend/src/lib/usePriceStream.ts` (quotes, 120-point history, status, rendered-direction flash), `components/Watchlist.tsx`, `WatchlistRow.tsx`, `PriceCell.tsx`, `Sparkline.tsx`, `Panel.tsx`, `Terminal.tsx` (main-chart placeholder with `data-ticker`)

### Established Patterns
- Short modules, concise docstrings, tests in `backend/tests/` with pytest-asyncio auto mode; frontend lint/typecheck/build as gates
- Verification on ports 8010+ (host port 8000 is the user's old container); stop servers by explicit PID, never `pkill -f uvicorn`
- `node`/`npm`/`npx` are wrappers around Windows binaries; cwd under /mnt/c; env vars need WSLENV to reach them

### Integration Points
- `test/e2e/02-watchlist.spec.ts` and `helpers.ts` define the watchlist test ids and API status codes
- `.planning/phases/01-live-price-terminal/01-UI-SPEC.md` and `01-UI-REVIEW.md` for tokens and the UI fixes listed above

</code_context>

<specifics>
## Specific Ideas

- Prior build pitfall: blocking sqlite calls in async handlers. Every DB call from an async path goes through `asyncio.to_thread`
- `db/finally.db` must stay gitignored; `db/.gitkeep` stays

</specifics>

<deferred>
## Deferred Ideas

- Tablet auto-collapse of the chat dock (UI-13, Phase 6)
- Dotted symbols like BRK.B (not needed for v1)

</deferred>
