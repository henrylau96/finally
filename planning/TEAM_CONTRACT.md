# Agent Team Contract

Shared interface contract for the FinAlly agent team. `PLAN.md` is the spec; this file pins the
details agents need to work in parallel. If you must change something here, edit this file and
message every affected teammate.

## Team, Names, Ownership

Only edit files you own. Need a change elsewhere? Message the owner (SendMessage, by name).

| Name | Role | Owns |
|------|------|------|
| `database` | Database Engineer | `backend/app/db/**`, `backend/tests/db/**` |
| `backend` | Backend API Engineer | `backend/app/main.py`, `backend/app/api/**`, `backend/app/portfolio/**`, `backend/tests/api/**`, `backend/tests/portfolio/**`, `backend/pyproject.toml` dependency list (others may `uv add` their own deps) |
| `llm` | LLM Engineer | `backend/app/llm/**`, `backend/tests/llm/**` |
| `frontend` | Frontend Engineer | `frontend/**` |
| `devops` | DevOps Engineer | `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `scripts/**`, `.env.example`, `db/.gitkeep`, `.gitignore`, root `README.md` |
| `tester` | Integration Tester | `test/**` |

Existing `backend/app/market/**` is done; do not modify it without telling `backend`.

**Git: do not commit or push.** The team lead commits. Everyone shares one working tree.
The local `origin` is the upstream course repo; push branches and open PRs on the fork `henrylau96/finally`.

## Environment (WSL2 on Windows)

- Python 3.14 (pinned in `backend/.python-version`): `cd backend && uv run ...` / `uv add ...` (uv at `~/.local/bin/uv`). Tests: `uv run --extra dev pytest`.
- Node is Windows-only: use `npm.cmd` / `npx.cmd` / `node.exe` (in `/mnt/c/Program Files/nodejs/`).
- Docker is Docker Desktop, Windows-only: use `docker.exe` (`/mnt/c/Users/fulai/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe`). Server is running.
- The root `.env` holds the user's `OPENROUTER_API_KEY` and a free-tier `MASSIVE_API_KEY` (never print them). Free tier gives static end-of-day prices; set `MASSIVE_API_KEY=` (empty) for the moving simulator. Use `LLM_MOCK=true` for anything automated.

## Backend Module Interfaces (Python)

### `app.db` (database)
SQLite via stdlib `sqlite3`. Schema per PLAN.md section 7. All functions take `user_id="default"`.
- DB path: env `DB_PATH`, default `<repo>/db/finally.db` (resolved relative to the backend dir). Creates the parent dir.
- `init_db()` - create tables if missing and seed (default user with 10000.0 cash, 10 default tickers). Idempotent. Called from app lifespan.
- `get_cash(user_id) -> float`, `set_cash(cash, user_id)`
- `get_watchlist(user_id) -> list[str]` (ordered by added_at), `add_to_watchlist(ticker, user_id) -> bool` (False if already present), `remove_from_watchlist(ticker, user_id) -> bool` (False if absent)
- `get_positions(user_id) -> list[dict]` (`ticker, quantity, avg_cost, updated_at`), `get_position(ticker, user_id) -> dict | None`
- `upsert_position(ticker, quantity, avg_cost, user_id)`, `delete_position(ticker, user_id)`
- `record_trade(ticker, side, quantity, price, user_id) -> dict` (returns the row incl. `id`, `executed_at`)
- `get_trades(user_id, limit=50) -> list[dict]`
- `record_snapshot(total_value, user_id)`, `get_snapshots(user_id) -> list[dict]` (`total_value, recorded_at`, ascending)
- `add_chat_message(role, content, actions: dict | None, user_id) -> dict`, `get_chat_messages(user_id, limit=20) -> list[dict]` (ascending, `actions` parsed back to dict/None)
- `transaction()` context manager (`BEGIN IMMEDIATE`): pass its connection as `conn=conn` to each repository call so a trade's cash + position + trade writes are atomic and serialized.

### `app.portfolio` (backend)
- `class TradeError(Exception)` - validation failure, message is user-facing.
- `execute_trade(ticker, side, quantity, price_cache, user_id="default") -> dict` - validates (known price, quantity > 0, enough cash / shares), updates cash + position (weighted avg cost; delete position at ~0 qty), records trade and a snapshot. Returns the trade dict. Raises `TradeError`.
- `get_portfolio(price_cache, user_id="default") -> dict` - the `GET /api/portfolio` body below.
- Background task snapshotting total value every 30s (started in lifespan).
- Watchlist service functions that also call `source.add_ticker` / `source.remove_ticker` so prices start/stop streaming. Do not remove a ticker from the market source if it is still held as a position.

### `app.llm` (llm)
- `async def handle_chat(message: str, price_cache, market_source, user_id="default") -> dict` - builds context, calls LLM (or mock), executes actions via `app.portfolio` functions, stores both messages via `app.db`, returns the `POST /api/chat` body below.
- `create_chat_router(price_cache, market_source) -> APIRouter` providing `POST /api/chat` and `GET /api/chat/history`. `backend` includes it in `main.py`.
- Use the `cerebras` skill (LiteLLM -> OpenRouter, `openrouter/openai/gpt-oss-120b`, Cerebras provider, structured outputs).
- **Mock mode (`LLM_MOCK=true`)** is deterministic, parsing the user message (case-insensitive):
  - `buy <qty> <TICKER>` / `sell <qty> <TICKER>` -> that trade
  - `add <TICKER>` / `remove <TICKER>` -> that watchlist change
  - otherwise no actions
  - `message` is always `"Mock response: <summary of actions or 'no actions'>"`

### `app.main` (backend)
- FastAPI app with lifespan: load `.env` from repo root (python-dotenv), `init_db()`, start market source with the DB watchlist + held tickers, start snapshot task, include routers, then mount static files.
- Static frontend served from env `STATIC_DIR`, default `backend/static`, mounted last at `/` with `html=True`. Skip mounting if the dir is missing (dev).
- Run: `cd backend && uv run uvicorn app.main:app --port 8000`.

## HTTP API (exact shapes)

Errors use FastAPI's `{"detail": "message"}`. Tickers are uppercased server-side.

- `GET /api/health` -> `{"status": "ok"}`
- `GET /api/stream/prices` -> SSE (existing). Each event: `data: {"AAPL": {"ticker","price","previous_price","timestamp","change","change_percent","direction"}, ...}`. `change` is vs previous tick; the frontend computes "daily change %" vs the first price it saw this session.
- `GET /api/portfolio` ->
  ```json
  {"cash_balance": 10000.0, "total_value": 10000.0, "total_unrealized_pnl": 0.0,
   "positions": [{"ticker": "AAPL", "quantity": 10, "avg_cost": 190.0, "current_price": 191.2,
                  "market_value": 1912.0, "unrealized_pnl": 12.0, "unrealized_pnl_percent": 0.63}]}
  ```
  (`unrealized_pnl_percent` is a percent, not a fraction. If no live price, use avg_cost.)
- `POST /api/portfolio/trade` body `{"ticker": "AAPL", "quantity": 10, "side": "buy"}` ->
  200 `{"trade": {"id","ticker","side","quantity","price","executed_at"}, "portfolio": <GET /api/portfolio body>}`; 400 on validation failure.
- `GET /api/portfolio/history` -> `[{"total_value": 10000.0, "recorded_at": "ISO"}]` ascending.
- `GET /api/watchlist` -> `[{"ticker","price","previous_price","change","change_percent","direction"}]` (price fields `null` if no price yet), in watchlist order.
- `POST /api/watchlist` body `{"ticker": "PYPL"}` -> 201 `{"ticker": "PYPL"}`; 409 if already present; 400 if invalid (must match `^[A-Z.]{1,10}$` after uppercasing).
- `DELETE /api/watchlist/{ticker}` -> 204; 404 if absent.
- `POST /api/chat` body `{"message": "..."}` ->
  ```json
  {"message": "text",
   "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10, "status": "executed", "price": 190.1, "error": null}],
   "watchlist_changes": [{"ticker": "PYPL", "action": "add", "status": "executed", "error": null}]}
  ```
  `status` is `"executed"` or `"failed"` (with `error` text).
- `GET /api/chat/history` -> `[{"id","role","content","actions","created_at"}]` ascending.

## Frontend Test IDs (for Playwright)

`frontend` must add these `data-testid` attributes; `tester` relies on them.

- Header: `total-value`, `cash-balance`, `connection-status` (with `data-status="connected|reconnecting|disconnected"`)
- Watchlist: `watchlist`, `watchlist-row-<TICKER>`, `price-<TICKER>`, `watchlist-add-input`, `watchlist-add-button`, `watchlist-remove-<TICKER>`
- Chart: `main-chart` (with `data-ticker="<selected>"`)
- Trade bar: `trade-ticker`, `trade-quantity`, `buy-button`, `sell-button`, `trade-error`
- Portfolio: `positions-table`, `position-row-<TICKER>`, `heatmap`, `heatmap-cell-<TICKER>` (with `data-pnl="positive|negative|flat"`), `pnl-chart`
- Chat: `chat-panel`, `chat-input`, `chat-send`, `chat-message` (with `data-role="user|assistant"`), `chat-loading`, `chat-action` (inline trade/watchlist confirmations)

## Docker Layout (devops)

- Frontend build: `frontend/` -> `npm run build` -> `frontend/out/` (Next.js `output: 'export'`).
- Image: backend at `/app/backend`, frontend export copied to `/app/backend/static`, `DB_PATH=/app/db/finally.db`, volume `finally-data:/app/db`, port 8000, `--env-file .env`.
- E2E: `test/docker-compose.test.yml` runs the app (with `LLM_MOCK=true`) plus a Playwright container.
