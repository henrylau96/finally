# Phase 1: Live Price Terminal - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning

<domain>
## Phase Boundary

User opens http://localhost:8000 and sees live simulated prices streaming into a dark terminal-style watchlist. Delivers: the GBM market simulator behind the abstract market-data interface, the shared price cache, the SSE stream, `/api/health`, FastAPI serving the Next.js static export from one origin, and the frontend shell with header connection dot and a live watchlist (flashing prices, daily change %, sparklines). Requirements: MKT-01..05, MKT-08, STRM-01..04, OPS-01, OPS-02, UI-01, UI-03, UI-04, TEST-01.

Not in this phase: SQLite and watchlist editing (Phase 2), trading and portfolio numbers (Phase 3), chat (Phase 4), Massive (Phase 5), Docker and E2E (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Market data engine
- Follow the prior design docs `planning/MARKET_INTERFACE.md` and `planning/MARKET_SIMULATOR.md`: abstract `MarketDataSource` (start / stop / add_ticker / remove_ticker / get_tickers); `PriceCache` as the single source of truth with a version counter for SSE change detection
- Correlated moves via Cholesky decomposition of a sector correlation matrix (tech 0.6, finance 0.5, cross-sector 0.3), using numpy
- Random shock events: ~0.1% chance per tick per ticker of a sudden 2-5% move
- Tickers are the 10 PLAN.md defaults, hardcoded until Phase 2 adds SQLite; realistic seed prices (AAPL ~$190, GOOGL ~$175, etc.) and per-ticker drift/volatility

### Stream contract
- `GET /api/stream/prices`: one SSE message per ~500ms tick whose data is a JSON map keyed by ticker; each value has `ticker, price, previous_price, timestamp, direction, day_change_pct`
- Daily change % is computed by the backend against the session-open price (seed price for the simulator)
- Server sends `retry: 1000`; client uses native EventSource retry. Connection dot: `connected` on open, `reconnecting` on error while EventSource retries, `disconnected` when closed
- `GET /api/health` returns exactly `{"status": "ok"}` (E2E `01-fresh-start.spec.ts` asserts this)

### Frontend foundation
- Next.js 16.4 App Router, React 19.3, TypeScript, `output: 'export'`, Tailwind 4.3 with theme tokens in CSS (PLAN.md colors: bg `#0d1117`/`#1a1a2e`, accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991`; no pure black)
- Sparklines: small inline SVG component, capped buffer (~120 points) accumulated from SSE since page load. Lightweight Charts 5.2 is reserved for the main chart and P&L chart in later phases
- Build the final terminal grid shell now (header, watchlist, main chart area, chat dock); only the header connection dot and the watchlist are live, the rest are labeled placeholders
- Use the E2E test ids from day one: `connection-status` with `data-status` (`connected` / `reconnecting` / `disconnected`), `watchlist-row-{TICKER}`, `price-{TICKER}`
- Price flash: apply a green/red background class on change and fade over ~500ms via CSS transition

### Project layout and dev loop
- `backend/` is a uv project with an `app/` package: `main.py`, `market/`, `api/`. FastAPI mounts the static export from `STATIC_DIR` (default `backend/static`) after the API routes
- Dev loop: `npm run build` produces `frontend/out`, which is copied or pointed to as the static dir so FastAPI serves everything from one origin; `next dev` rewrites `/api/*` to `http://localhost:8000` for fast UI iteration
- Python deps via `uv add`: fastapi, uvicorn[standard], numpy; dev: pytest, pytest-asyncio, httpx
- Tests in this phase: backend pytest for market data (TEST-01). Frontend tests come with TEST-05 in Phase 6

### Claude's Discretion
- Exact module split inside `app/market/`, the SSE implementation (StreamingResponse vs sse library), and component structure inside `frontend/src/`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- No application code exists: `backend/` and `frontend/` were deleted for the from-scratch rebuild
- Design references: `planning/MARKET_INTERFACE.md`, `planning/MARKET_SIMULATOR.md`, `planning/MARKET_DATA_DESIGN.md`, `planning/MARKET_DATA_SUMMARY.md`
- Prior implementation map (reference only, does not describe current tree): `.planning/reference/codebase-prior/`
- Scaffolding kept: `Dockerfile` (expects `frontend/` with `npm run build` -> `out/`, and `backend/` with `pyproject.toml` + `uv.lock`, `STATIC_DIR=/app/backend/static`), `test/e2e/*.spec.ts`

### Established Patterns
- User code style: simple, short modules and functions, concise docstrings, no emojis, no defensive programming, latest APIs; always `uv run` / `uv add`
- Backend pins Python 3.14

### Integration Points
- E2E specs (`test/e2e/01-fresh-start.spec.ts`, `06-sse-reconnect.spec.ts`, `helpers.ts`) define the testids and the health response
- Environment: WSL2 on `/mnt/c`. `node`, `npm`, `npx`, `docker`, `gsd-sdk` in `~/.local/bin` are wrappers that run the Windows binaries (Node 24, npm 11); run them from a cwd under `/mnt/c`. `node_modules` will contain Windows-native binaries, so keep `node_modules` out of Docker build contexts. uv is at `~/.local/bin/uv`

</code_context>

<specifics>
## Specific Ideas

- Visual target: Bloomberg-terminal density, dark, every pixel earns its place
- The `.gitignore` has a Python `lib/` rule that previously hid `frontend/src/lib`; make sure frontend `lib` folders are not ignored

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
