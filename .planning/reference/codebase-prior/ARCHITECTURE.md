<!-- refreshed: 2026-10-19 -->
# Architecture

**Analysis Date:** 2026-10-19

**Frontend status:** `frontend/` is ABSENT (deleted in HEAD commit 4619f5b so it can be rebuilt). The backend, Dockerfile, scripts and E2E tests exist and already assume a Next.js static export. See "Frontend Contract" below.

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│  Browser (frontend/ - NOT PRESENT; to be rebuilt)            │
│  EventSource /api/stream/prices  +  fetch /api/*             │
└────────────────────────────┬────────────────────────────────┘
                             │ same origin, port 8000
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI app  `backend/app/main.py`                          │
│  Routers: health, stream, portfolio, watchlist, chat         │
│  StaticFiles mount "/" (only if static dir exists)           │
├──────────────┬───────────────────┬──────────────────────────┤
│ `app/api/`   │ `app/llm/`        │ `app/market/stream.py`   │
│ REST routes  │ chat orchestration│ SSE generator            │
└──────┬───────┴─────────┬─────────┴───────────┬──────────────┘
       ▼                 ▼                     │ reads
┌──────────────────────────────────┐           ▼
│ Service layer `app/portfolio/`    │   ┌─────────────────────┐
│ trading, watchlist, snapshots     │──▶│ PriceCache          │
└──────────────┬───────────────────┘   │ `market/cache.py`   │
               ▼                        └──────────▲──────────┘
┌──────────────────────────────────┐               │ writes
│ Persistence `app/db/`             │   ┌──────────┴──────────┐
│ SQLite `db/finally.db`            │   │ MarketDataSource    │
└──────────────────────────────────┘   │ Simulator | Massive │
                                        └─────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| App wiring and lifespan | Builds singletons, mounts routers and static files, starts/stops background work | `backend/app/main.py` |
| Market interface | ABC `MarketDataSource` (start/stop/add_ticker/remove_ticker/get_tickers) | `backend/app/market/interface.py` |
| Price cache | Thread-safe latest price per ticker with monotonic `version` | `backend/app/market/cache.py` |
| Source factory | Chooses Massive when `MASSIVE_API_KEY` non-empty, else simulator | `backend/app/market/factory.py` |
| Simulator | GBM prices, correlated moves, random events, ~500ms tick | `backend/app/market/simulator.py` |
| Massive client | REST polling (default 15s, `MASSIVE_POLL_INTERVAL`) | `backend/app/market/massive_client.py` |
| SSE stream | Pushes full price map every 0.5s when cache version changes | `backend/app/market/stream.py` |
| Trading service | Validates and executes market orders, builds portfolio view | `backend/app/portfolio/trading.py` |
| Watchlist service | Keeps DB watchlist and market source tickers in sync | `backend/app/portfolio/watchlist.py` |
| Snapshot loop | Records total value every 30s | `backend/app/portfolio/snapshots.py` |
| Repository | SQL functions per table, optional shared `conn` | `backend/app/db/repository.py` |
| Connection/init | `transaction()` (BEGIN IMMEDIATE), `init_db()` lazy schema + seed | `backend/app/db/connection.py`, `backend/app/db/schema.sql` |
| Chat orchestration | Context -> LLM -> execute actions -> persist | `backend/app/llm/chat.py` |
| LLM client | LiteLLM `acompletion` to `openrouter/openai/gpt-oss-120b`, Cerebras provider, structured output | `backend/app/llm/client.py` |
| Mock LLM | Regex parser for "buy N TICKER", "add/remove TICKER" when `LLM_MOCK=true` | `backend/app/llm/mock.py` |

## Pattern Overview

**Overall:** Layered modular monolith (routes -> services -> repository) with a single in-process producer/consumer price pipeline.

**Key Characteristics:**
- Router factories (`create_*_router(price_cache, ...)`) inject dependencies by closure; no FastAPI `Depends`.
- Module-level singletons `price_cache` and `market_source` in `backend/app/main.py`.
- Strategy pattern for market data (`MarketDataSource` ABC); downstream code only reads `PriceCache`.
- Sync SQLite (stdlib `sqlite3`), no ORM; every repo function takes optional `conn` to join a caller's transaction.
- Every table carries `user_id` defaulting to `"default"`; all service functions accept `user_id="default"`.
- Each package re-exports its public API via `__init__.py` (`__all__`).

## Layers

**API layer:**
- Purpose: HTTP translation, request models, error to status mapping
- Location: `backend/app/api/`, `backend/app/llm/router.py`, `backend/app/market/stream.py`
- Depends on: `app.portfolio`, `app.db`, `app.market`, `app.llm.chat`

**Service layer:**
- Purpose: business rules (trade validation, avg cost, valuation, watchlist/source sync)
- Location: `backend/app/portfolio/`, `backend/app/llm/chat.py`
- Depends on: `app.db`, `app.market`

**Persistence layer:**
- Purpose: SQLite access, schema, seed
- Location: `backend/app/db/`
- Depends on: stdlib only

**Market data layer:**
- Purpose: produce prices into `PriceCache`
- Location: `backend/app/market/`
- Depends on: `numpy`, `massive` SDK

## Data Flow

### Trade (manual)

1. `POST /api/portfolio/trade` body `{ticker, quantity, side}` (`backend/app/api/portfolio.py`)
2. `execute_trade` validates side/quantity, reads price from `PriceCache`, raises `TradeError` if none (`backend/app/portfolio/trading.py`)
3. Inside `db.transaction()`: update cash and position, `record_trade`, `record_snapshot`
4. Returns `{"trade": ..., "portfolio": ...}`; `TradeError` becomes HTTP 400 `{detail}`

### Price streaming

1. Source task writes `PriceCache.update()` (~500ms simulator, 15s default Massive)
2. `GET /api/stream/prices` emits `retry: 1000`, then `data: {TICKER: {ticker, price, previous_price, timestamp, ...}}` whenever `cache.version` changes (`backend/app/market/stream.py`)

### Chat

1. `POST /api/chat {message}` (`backend/app/llm/router.py`)
2. `handle_chat`: mock or `call_llm` with portfolio, watchlist and last 20 messages (`backend/app/llm/prompt.py`)
3. Stores user message; runs watchlist changes first, then trades (each reports `status` executed/failed with `error`)
4. Stores assistant message with `actions` JSON; returns `{message, trades, watchlist_changes}`
5. LLM failure or malformed JSON yields a friendly message with no actions

### Lifespan

`db.init_db()` -> `market_source.start(tracked_tickers())` (watchlist + held tickers) -> `snapshot_loop` task; on shutdown cancel the task and `market_source.stop()`.

**State Management:** Durable state in SQLite; live prices only in memory (`PriceCache`); no server sessions.

## Key Abstractions

**MarketDataSource / PriceCache / PriceUpdate:** `backend/app/market/interface.py`, `cache.py`, `models.py` (`PriceUpdate` immutable dataclass with `change`, `change_percent`, `direction`, `to_dict()`).

**ChatResponse schema:** pydantic structured output `{message, trades[], watchlist_changes[]}` in `backend/app/llm/schema.py`.

**TradeError:** user-facing validation exception in `backend/app/portfolio/trading.py`.

## Entry Points

**ASGI app:** `backend/app/main.py` (`app.main:app`), run by `uvicorn app.main:app --host 0.0.0.0 --port 8000` (Docker CMD in `Dockerfile`).

**Demo script:** `backend/market_data_demo.py` (Rich terminal dashboard).

**Containers:** `scripts/start_mac.sh`, `scripts/start_windows.ps1`, `docker-compose.yml`, `test/docker-compose.test.yml`.

## Frontend Contract (for the rebuild)

**Static serving:** `main.py` mounts `StaticFiles(directory=STATIC_DIR, html=True)` at `/` only if the directory exists. `STATIC_DIR` defaults to `backend/static/` (gitignored); Docker sets `STATIC_DIR=/app/backend/static`. The Dockerfile stage 1 runs `npm ci` + `npm run build` in `/app/frontend` and copies `frontend/out` to `backend/static`, so the new frontend MUST have `frontend/package.json`, `frontend/package-lock.json` and a Next.js `output: 'export'` build emitting `frontend/out/`. The static mount is registered last so `/api/*` routes win.

**Endpoints:**
- `GET /api/health` -> `{status: "ok"}`
- `GET /api/stream/prices` (SSE) -> map of ticker to `{ticker, price, previous_price, timestamp, ...}`
- `GET /api/portfolio` -> `{cash_balance, total_value, total_unrealized_pnl, positions[{ticker, quantity, avg_cost, current_price, market_value, unrealized_pnl, unrealized_pnl_percent}]}`
- `POST /api/portfolio/trade` `{ticker, quantity, side}` -> `{trade, portfolio}`; 400 `{detail}` on error
- `GET /api/portfolio/history` -> `[{total_value, recorded_at}]`
- `GET /api/watchlist` -> `[{ticker, price, previous_price, change, change_percent, direction}]` (nulls until first price)
- `POST /api/watchlist {ticker}` -> 201 `{ticker}`; 400 invalid, 409 duplicate
- `DELETE /api/watchlist/{ticker}` -> 204; 404 if absent
- `POST /api/chat {message}` -> `{message, trades[{ticker, side, quantity, status, price, error}], watchlist_changes[{ticker, action, status, error}]}`
- `GET /api/chat/history` -> `[{id, role, content, actions, created_at}]` (limit 100)

**E2E test ids the UI must provide** (from `test/e2e/*.spec.ts`): `connection-status` (attribute `data-status="connected"`), `cash-balance`, `total-value`, `price-{TICKER}`, `watchlist-row-{TICKER}`, `watchlist-add-input`, `watchlist-add-button`, `main-chart` (`data-ticker`), `trade-ticker`, `trade-quantity`, `trade-error`, `position-row-{TICKER}`, `heatmap`, `heatmap-cell-{TICKER}` (`data-pnl` positive|negative|flat), `pnl-chart` (`data-points`, contains canvas/svg), `chat-panel`, `chat-input`, `chat-send`, `chat-loading`, `chat-message` (`data-role` user|assistant), `chat-action` (`data-ok`). `buy-button`, `sell-button` (used by `uiTrade` in `test/e2e/helpers.ts`).

## Architectural Constraints

- **Threading:** Single asyncio event loop; sync route handlers run in the threadpool; `PriceCache` is thread-safe. SQLite writes serialized with `BEGIN IMMEDIATE`.
- **Global state:** `price_cache`, `market_source` in `backend/app/main.py`; `.env` loaded at import from repo root via `python-dotenv`.
- **Single user:** `user_id="default"` hardcoded in routers; `chat/router.py` and API routers do not pass user ids.
- **Config via env:** `DB_PATH` (default `<repo>/db/finally.db`), `STATIC_DIR`, `LLM_MOCK`, `MASSIVE_API_KEY`, `MASSIVE_POLL_INTERVAL`, `OPENROUTER_API_KEY`.
- **Circular imports:** none detected; `app.market` has no dependency on `app.db`.

## Anti-Patterns

### Importing the app module in tests without isolating env

**What happens:** `main.py` builds `price_cache`/`market_source` and loads `.env` at import time.
**Why it's wrong:** Real keys and a real DB path can leak into tests.
**Do this instead:** Follow `backend/tests/conftest.py` and `backend/tests/api/test_routes.py` (set `DB_PATH`/`LLM_MOCK` before use).

## Error Handling

**Strategy:** Domain exceptions mapped to HTTP codes at the router; LLM failures degrade to a message.

**Patterns:**
- `TradeError`/`ValueError` -> 400; duplicate watchlist -> 409; missing -> 404
- Snapshot loop logs and continues on exceptions (`snapshots.py`)
- Chat actions report per-item failure in the response rather than failing the request

## Cross-Cutting Concerns

**Logging:** stdlib `logging` with `logger = logging.getLogger(__name__)`.
**Validation:** pydantic request models; ticker regex `^[A-Z.]{1,10}$` (`portfolio/watchlist.py`).
**Authentication:** None (single-user).

---

*Architecture analysis: 2026-10-19*
