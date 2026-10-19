# Walking Skeleton - FinAlly (AI Trading Workstation)

**Phase:** 1
**Generated:** 2026-10-19

## Capability Proven End-to-End

A user opens the FastAPI server's root URL and sees a dark terminal page whose 10 watchlist prices update live from a GBM simulator, through an in-memory price cache and an SSE stream, all served from one origin.

The skeleton's "real read/write" is the price cache: the simulator background task writes every ~500ms (`PriceCache.update`), the SSE route reads (`PriceCache.get_all` on `version` change), and the browser consumes it with `EventSource`. There is no database in Phase 1 by locked decision; SQLite arrives in Phase 2.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI 0.146 on uvicorn 0.54 (Python 3.14, uv project in `backend/`, virtual project, `uv run` / `uv add` only) | Locked stack; native SSE (`fastapi.sse.EventSourceResponse`) since 0.135 removes the need for an SSE library |
| Frontend framework | Next.js 16.4 App Router, React 19.3, TypeScript ~5.9 (pinned: TS 7 breaks eslint-config-next), Tailwind 4.3 with `@theme` tokens in `src/app/globals.css` | Locked stack; static export keeps one origin and one container |
| Serving model | `output: "export"` -> `frontend/out`; FastAPI mounts it with `StaticFiles(html=True, check_dir=False)` at `/`, registered after all `/api/*` routers; dir from `STATIC_DIR` env (default `backend/static`, Docker sets `/app/backend/static`) | Single origin, no CORS, matches the kept Dockerfile |
| Real-time transport | SSE at `GET /api/stream/prices`; one message per ~500ms tick; `data` is a JSON map keyed by ticker with exactly `ticker, price, previous_price, timestamp, direction, day_change_pct`; first event carries `retry: 1000` | One-way push; native EventSource reconnect; locked contract |
| Market data | `MarketDataSource` ABC (start / stop / add_ticker / remove_ticker / get_tickers) + `create_market_data_source(cache)` factory; `SimulatorDataSource` wraps `GBMSimulator` (Cholesky-correlated GBM, 0.1% shocks of 2-5%) | Massive client (Phase 5) plugs in behind the same interface; downstream code never sees the source |
| Shared state | `PriceCache` (thread lock, `version` counter, session-open per ticker for `day_change_pct`) is the single source of truth for prices | SSE, and later portfolio/trades/chat, read prices only from the cache |
| Data layer | None in Phase 1; tickers hardcoded as `DEFAULT_TICKERS` (backend `app/market/seed_prices.py`, frontend `src/lib/tickers.ts`) | Locked: SQLite and the persistent watchlist are Phase 2 |
| Auth | None (single user, `user_id="default"` from Phase 2 on) | Product spec: no login |
| Deployment target (this phase) | Documented local run: `cd backend && STATIC_DIR=../frontend/out uv run uvicorn app.main:app --port 8000 --timeout-graceful-shutdown 2` after `cd frontend && npm run build`. Docker image, start/stop scripts are Phase 6 | `--timeout-graceful-shutdown 2` is required: uvicorn otherwise hangs on shutdown with an open SSE client |
| Dev loop | `npm run dev` uses a phase-aware `next.config.ts` that rewrites `/api/*` to `http://localhost:8000` only for the dev server; `next build` gets `output: "export"` | Clean build output and fast UI iteration |
| Directory layout | `backend/app/{main.py, market/, api/}`, `backend/tests/{market/, test_health.py}`; `frontend/src/{app/, components/, lib/}` (`!frontend/src/lib/` negation keeps lib tracked) | Short modules per CLAUDE.md; matches PLAN.md directory boundaries |
| Tests | Backend pytest 9 + pytest-asyncio 1.4 (`asyncio_mode = "auto"`, `pythonpath = ["."]`); SSE logic tested via the `price_events` generator, HTTP layer via curl smoke; frontend gated by eslint + `tsc --noEmit` + `next build` until TEST-05 | Fast, deterministic feedback; Playwright suite consolidated in Phase 6 |
| UI test hooks | `connection-status` (`data-status`), `watchlist-row-{TICKER}`, `price-{TICKER}` (text = price only), `total-value`, `cash-balance`, `main-chart` (`data-ticker`), `heatmap`, `pnl-chart`, `chat-panel` | E2E specs in `test/e2e/` already depend on these |

## Stack Touched in Phase 1

- [ ] Project scaffold (uv backend with pytest; Next.js frontend with eslint, typecheck, static build) - plans 01-01, 01-02
- [ ] Routing - `GET /api/health`, `GET /api/stream/prices`, static `/` - plan 01-01, 01-02
- [ ] Data read/write - price cache written by the simulator task and read by the SSE route (no DB this phase by locked decision) - plan 01-01
- [ ] UI - live watchlist wired to the SSE API via EventSource, connection indicator, row selection and chat-dock toggle - plans 01-02, 01-04
- [ ] Deployment - documented local full-stack run command on one origin - plan 01-05

## Out of Scope (Deferred to Later Slices)

- SQLite schema, seed data, persistent watchlist add/remove UI and API (Phase 2)
- Main price chart with Lightweight Charts and real row-click chart switching (Phase 2)
- Trading, positions, cash, total value, heatmap, P&L chart and snapshots (Phase 3)
- AI chat and LLM mock mode (Phase 4)
- Massive REST poller and `MASSIVE_API_KEY` source selection (Phase 5)
- Dockerfile changes (including adding `--timeout-graceful-shutdown 2` to the CMD), start/stop scripts, `.dockerignore`, tablet layout, frontend unit tests, Playwright suite via docker-compose (Phase 6)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2: User edits a persistent SQLite-backed watchlist (add/remove reach `MarketDataSource.add_ticker/remove_ticker`) and inspects a ticker in the main chart
- Phase 3: User buys and sells at the cached market price and sees positions, heatmap, P&L chart and live header totals
- Phase 4: User chats with FinAlly, which trades and edits the watchlist through the same services
- Phase 5: User with a Massive key gets real prices through the same `MarketDataSource` interface and cache
- Phase 6: Anyone runs the whole app with one Docker command, data persists, and the full test suite passes
