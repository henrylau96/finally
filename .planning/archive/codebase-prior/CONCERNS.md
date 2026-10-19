# Codebase Concerns

**Analysis Date:** 2026-10-19

## Tech Debt

**Frontend absent (primary gap):**
- Issue: `frontend/` was deleted in commit 4619f5b so it can be rebuilt. No UI exists.
- Files: `Dockerfile` (stage 1 does `COPY frontend/package.json ...`, `npm ci`, `npm run build`, then `COPY --from=frontend /app/frontend/out ./static`), `test/e2e/*.spec.ts`, `backend/app/main.py` (mounts `StaticFiles` only if `static_dir.is_dir()`).
- Impact: `docker build` fails at stage 1. The app serves the API only when run locally, because the static mount is skipped silently. All six Playwright specs in `test/e2e/` (01-fresh-start through 06-sse-reconnect) have nothing to test. `scripts/start_*.sh|ps1` and `docker-compose.yml` cannot produce a working image.
- Fix approach: Rebuild `frontend/` as a Next.js static export (`output: 'export'`, so `out/` exists). The rebuilt UI must match the selectors and DOM contracts in `test/e2e/helpers.ts` and the specs. Per PLAN.md section 10 it consumes `/api/stream/prices` (an SSE event is a dict keyed by ticker), `/api/portfolio`, `/api/portfolio/trade`, `/api/portfolio/history`, `/api/watchlist`, `/api/chat` and `/api/chat/history`.

**Silent missing-static behaviour:**
- Issue: `backend/app/main.py` skips the static mount without any log when `STATIC_DIR` or `backend/static` is absent.
- Impact: A broken image that is missing the frontend still starts and answers `/api/health`.
- Fix approach: Log a warning when the directory is missing.

**Sync SQLite called from async handlers:**
- Issue (verified): `handle_chat` in `backend/app/llm/chat.py` is `async` but calls blocking sqlite code directly: `db.add_chat_message`, `db.get_chat_messages`, `execute_trade`, `get_portfolio`. The `/api/chat` and `/api/chat/history` routes in `backend/app/llm/router.py` are `async def` and call `db.*` the same way. `BEGIN IMMEDIATE` in `backend/app/db/connection.py` can block the event loop while another writer holds the lock, including the SSE loop and the snapshot loop. `snapshot_loop` in `backend/app/portfolio/snapshots.py` also calls `db.record_snapshot` synchronously inside a coroutine.
- Impact: Latency spikes under contention. This is low severity for a single user.
- Fix approach: Wrap the db calls in `asyncio.to_thread`, or make the chat helpers sync and call them via `run_in_threadpool`. The REST routes in `backend/app/api/portfolio.py` are plain `def`, so they already run in the threadpool.

**Unbounded portfolio snapshot history:**
- Issue (verified): `db.get_snapshots` in `backend/app/db/repository.py` runs `SELECT ... ORDER BY recorded_at` with no LIMIT. `GET /api/portfolio/history` returns every row. The snapshot loop writes one row every 30s (about 2,880 rows per day) and every trade writes another. Nothing prunes or downsamples old rows.
- Impact: The payload and query time grow without bound on a long-lived volume. The P&L chart gets slower to load.
- Fix approach: Add a LIMIT or time window to the query, downsample on read, or prune old rows in the loop.

**Sold-out ticker not on the watchlist keeps streaming:**
- Issue (verified): `_sell` in `backend/app/portfolio/trading.py` deletes the position but never calls `source.remove_ticker`. `remove_watchlist_ticker` in `backend/app/portfolio/watchlist.py` keeps streaming a ticker while it is held, but the reverse path (selling the last share of an unwatched ticker) has no hook. `execute_trade` has no access to the market source.
- Impact: Orphan tickers stay in the simulator and cache, in the SSE payload and in the Massive poll list until restart. After a restart `tracked_tickers()` drops them. This is a leak and not a correctness bug.
- Fix approach: After a sell that empties the position, remove the ticker from the source if it is not in `db.get_watchlist`. This needs the source passed into the trade path, or a post-trade hook in the API and chat layers.

## Known Bugs

**Massive snapshot None timestamps:**
- Symptoms (verified): `snapshot_price` in `backend/app/market/massive_client.py` returns `(price, None)` for the `day.close`, `prev_day.close` and EOD paths. `PriceCache.update` in `backend/app/market/cache.py` does `ts = timestamp or time.time()`, so the stale close is stamped as "now".
- Impact: The UI cannot tell stale or end-of-day prices from live ones. No crash. A genuine timestamp of 0 would also be replaced, which is harmless.
- Fix approach: Carry the real data timestamp or a `stale` flag in `PriceUpdate`. Alternatively, use an explicit `if timestamp is None` check and expose the staleness to the client.

**No price seed on Massive add_ticker:**
- Symptoms (verified): `MassiveDataSource.add_ticker` seeds the cache only when the ticker is in `self._eod_closes`, which is populated only in eod mode. In snapshot mode there is no seed and no immediate poll. The simulator seeds immediately (`backend/app/market/simulator.py` line 242 onward).
- Impact: A newly added ticker has no price until the next poll (15s by default), and with the free tier's 900s EOD interval it can wait up to 15 minutes. During that window `execute_trade` raises `No price available for <ticker>`, and `get_watchlist_with_prices` returns null price fields. `handle_chat` in `backend/app/llm/chat.py` runs watchlist changes before trades, so an LLM "add and buy" in one turn fails on Massive.
- Fix approach: In `add_ticker`, fetch the single ticker immediately via `asyncio.to_thread`, or trigger `_poll_once`.

**Ticker pattern rejects some valid symbols:**
- Symptoms: `TICKER_PATTERN = ^[A-Z.]{1,10}$` in `backend/app/portfolio/watchlist.py` rejects symbols with digits or hyphens. Trades via `execute_trade` skip this validation but are limited by the price cache.
- Impact: Low.

## Security Considerations

**No authentication or rate limiting:**
- Risk: All `/api/*` endpoints, including `/api/chat` (which spends OpenRouter credits and auto-executes trades), are open. This is by design for a single-user local app (PLAN.md). Exposing the container beyond localhost, for example the cloud deployment stretch goal, would be unsafe.
- Files: `backend/app/main.py`, `backend/app/llm/router.py`.
- Recommendations: Bind to localhost in the start scripts, and add a token or rate limit before any public deployment.

**Unvalidated input sizes:**
- Risk: `ChatRequest.message` in `backend/app/llm/router.py` has `min_length=1` but no `max_length`. `TradeRequest.quantity` is a float with no upper bound or `gt=0` at the schema level (checked later in `execute_trade`).
- Recommendations: Add `max_length` and `Field(gt=0)`.

**Secrets handling:**
- `.env` is gitignored and `.env.example` is committed with blank values. The OpenRouter and Massive keys are read from the environment. Nothing in the code logs them.

## Performance Bottlenecks

**SSE per-client polling:**
- Problem: `_generate_events` in `backend/app/market/stream.py` wakes every 0.5s per client and calls `request.is_disconnected()`. It serializes all tickers on each cache version change. The simulator bumps the version about every 500ms, so effectively every tick.
- Cause: There is no shared broadcast. Cost is O(clients x tickers).
- Improvement path: This is fine for single-user. Use a shared broadcaster if multi-user is ever needed.

**New SQLite connection per operation:**
- Problem: `connect()` in `backend/app/db/connection.py` opens a new connection on every call. `init_db` re-reads and executes `schema.sql`. WAL mode and `busy_timeout` are not set.
- Impact: Concurrent writers can raise `database is locked` after the default 5s timeout. `backend/tests/portfolio/test_concurrency.py` covers trades.

## Fragile Areas

**LLM response handling:**
- Files: `backend/app/llm/client.py`, `backend/app/llm/chat.py`.
- Why fragile: `parse_response` catches only `ValidationError`. `get_response` catches every exception and returns a fixed "unavailable" message. The user message is persisted only after the LLM call returns, and the persisted history excludes the current message during prompt building. Trades from the LLM run sequentially with no cap on count or size. The model name and provider routing are hard-coded in `MODEL` and `EXTRA_BODY`.
- Safe modification: Keep the `ChatResponse` schema (`backend/app/llm/schema.py`) in sync with the prompt in `backend/app/llm/prompt.py` and the mock in `backend/app/llm/mock.py`.

**Price fallback in valuation:**
- Files: `backend/app/portfolio/trading.py`.
- Why fragile: `_position_view` uses `price_cache.get_price(...) or avg`. If a held ticker has no cached price (for example after Massive removal or a failed poll), it is silently valued at cost, showing 0 P&L and distorting the total value and snapshots.

**Module-level singletons:**
- Files: `backend/app/main.py` creates `price_cache` and `market_source` at import time. `create_market_data_source` in `backend/app/market/factory.py` reads env vars at import, so tests must patch the environment before import. The stream router in `backend/app/market/stream.py` registers routes on a module-global `router`, so calling `create_stream_router` twice would duplicate routes.

**Python 3.14 dependency:**
- Files: `backend/.python-version`, `Dockerfile` (`python:3.14-slim`), `backend/pyproject.toml`.
- Risk: Newer interpreter with native-wheel availability risk for dependencies such as numpy, litellm and massive. The `ghcr.io/astral-sh/uv:latest` image tag is unpinned.

## Scaling Limits

- Single-user only: `user_id="default"` is hard-coded in `backend/app/api/*.py` and `backend/app/llm/router.py`, and SQLite is a single file. Massive free tier is limited to 5 calls/min, and the poller uses one call per poll.

## Dependencies at Risk

- `ghcr.io/astral-sh/uv:latest` in `Dockerfile` is unpinned and builds are not reproducible.
- `litellm` is heavy and slow to import (imported lazily in `backend/app/llm/client.py`).

## Missing Critical Features

- The entire frontend (see Tech Debt).
- Real-LLM integration tests. Only mock mode and parsing are tested (`backend/tests/llm/`).
- `planning/` has no phase docs for the frontend rebuild.

## Test Coverage Gaps

**E2E suite cannot run:**
- Files: `test/e2e/*.spec.ts`, `test/docker-compose.test.yml`.
- What's not tested: Everything end to end, because the image cannot build without `frontend/`.
- Priority: High, until the frontend returns.

**Backend gaps:**
- Not covered by an obvious test: the lifespan and static mount in `backend/app/main.py`, the SSE generator behaviour on disconnect (`backend/app/market/stream.py`), `snapshot_loop`, and the sold-out ticker lifecycle.
- Priority: Medium.

**Frontend unit tests:** Not applicable until `frontend/` exists.

---

*Concerns audit: 2026-10-19*
