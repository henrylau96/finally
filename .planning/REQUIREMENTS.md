# Requirements: FinAlly — AI Trading Workstation

**Defined:** 2026-10-19
**Core Value:** From one command, the user lands in a live, dark trading terminal where prices stream, trades fill instantly, and the AI copilot can trade for them through chat.
**Source of truth:** `planning/PLAN.md` (section numbers cited as §N)

## v1 Requirements

### Market Data (§6)

- [x] **MKT-01**: Simulator and Massive client implement one abstract market-data interface; downstream code is agnostic to the source
- [x] **MKT-02**: Simulator generates prices by geometric Brownian motion with per-ticker drift and volatility, updating ~every 500ms
- [x] **MKT-03**: Simulator moves related tickers together (correlated moves, e.g. tech stocks)
- [x] **MKT-04**: Simulator occasionally applies a sudden 2-5% move to a ticker
- [x] **MKT-05**: Simulator starts from realistic seed prices (e.g. AAPL ~$190, GOOGL ~$175)
- [ ] **MKT-06**: When `MASSIVE_API_KEY` is set and non-empty the backend uses the Massive REST poller; otherwise it uses the simulator
- [ ] **MKT-07**: Massive poller fetches the union of watched tickers on a configurable interval (free tier: grouped daily bars every 15 min; paid: 2-15s) and parses responses into the simulator's format
- [x] **MKT-08**: A single background task writes to an in-memory price cache holding latest price, previous price and timestamp per ticker
- [ ] **MKT-09**: A newly added ticker gets a price in the cache without waiting for the next long poll cycle, and prices carry their true source timestamp (no stale price shown as live)

### Streaming (§6)

- [x] **STRM-01**: `GET /api/stream/prices` is a long-lived SSE stream consumable by native `EventSource`
- [x] **STRM-02**: The stream pushes updates for all tickers known to the system at ~500ms cadence
- [x] **STRM-03**: Each event contains ticker, price, previous price, timestamp and change direction
- [x] **STRM-04**: Clients reconnect automatically after a dropped connection (EventSource retry)

### Database (§7)

- [x] **DATA-01**: SQLite file at `db/finally.db` is created with schema and seed data on first start or first request if missing or empty; no manual migration step
- [x] **DATA-02**: Schema has tables `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages` with the PLAN.md columns; every table carries `user_id` defaulting to `"default"`
- [x] **DATA-03**: Seed creates user `default` with $10,000 cash and watchlist AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX
- [ ] **DATA-04**: Data persists across container restarts via the mounted `db/` volume

### Portfolio (§8)

- [ ] **PORT-01**: `GET /api/portfolio` returns positions, cash balance, total value and unrealized P&L
- [ ] **PORT-02**: User can buy shares with a market order `{ticker, quantity, side}` via `POST /api/portfolio/trade`; it fills instantly at the current price, no fees
- [ ] **PORT-03**: User can sell shares the same way; selling all shares removes the position
- [ ] **PORT-04**: Fractional quantities are supported; average cost updates correctly on repeated buys
- [ ] **PORT-05**: A buy with insufficient cash or a sell exceeding held shares is rejected with a clear error and no state change
- [ ] **PORT-06**: Every trade is appended to the `trades` log
- [ ] **PORT-07**: Portfolio value is snapshotted every 30 seconds and immediately after each trade
- [ ] **PORT-08**: `GET /api/portfolio/history` returns snapshots for the P&L chart in bounded size

### Watchlist (§8)

- [x] **WATCH-01**: `GET /api/watchlist` returns watched tickers with latest prices
- [x] **WATCH-02**: User can add a ticker via `POST /api/watchlist {ticker}`; it starts streaming
- [x] **WATCH-03**: User can remove a ticker via `DELETE /api/watchlist/{ticker}`
- [x] **WATCH-04**: Duplicate adds are handled gracefully (unique per user and ticker)

### AI Chat (§9)

- [ ] **CHAT-01**: `POST /api/chat` returns one complete JSON response (message plus executed actions); no token streaming
- [ ] **CHAT-02**: The prompt includes a FinAlly system prompt, current portfolio context (cash, positions with P&L, watchlist with live prices, total value) and recent conversation history
- [ ] **CHAT-03**: The LLM is called via LiteLLM -> OpenRouter `openrouter/openai/gpt-oss-120b` with Cerebras as provider, using structured output `{message, trades[], watchlist_changes[]}`
- [ ] **CHAT-04**: Trades from the LLM auto-execute through the same validation as manual trades; failures are reported back in the response
- [ ] **CHAT-05**: Watchlist changes from the LLM auto-execute
- [ ] **CHAT-06**: User and assistant messages, with assistant actions as JSON, are stored in `chat_messages`
- [ ] **CHAT-07**: Malformed LLM output is handled gracefully with an error message instead of a crash
- [ ] **CHAT-08**: With `LLM_MOCK=true` the backend returns deterministic mock responses (including a trade) without calling OpenRouter
- [ ] **CHAT-09**: The chat request does not block the event loop (price streaming continues during an LLM call)

### Frontend (§2, §10)

- [x] **UI-01**: Single-page Next.js TypeScript app built as a static export, styled with Tailwind using the PLAN.md dark theme and colors
- [ ] **UI-02**: Header shows live portfolio total value, cash balance and a connection dot (green connected, yellow reconnecting, red disconnected)
- [x] **UI-03**: Watchlist panel shows each ticker's symbol, current price, daily change % and a sparkline accumulated from SSE since page load
- [x] **UI-04**: Prices flash green on uptick or red on downtick, fading over ~500ms via CSS transition
- [x] **UI-05**: User can add and remove watchlist tickers from the watchlist panel
- [ ] **UI-06**: Clicking a ticker shows a larger price-over-time chart for it in the main chart area
- [ ] **UI-07**: Trade bar has ticker and quantity fields plus buy and sell buttons; orders fill instantly with no confirmation and errors are shown inline
- [ ] **UI-08**: Positions table shows ticker, quantity, average cost, current price, unrealized P&L and % change
- [ ] **UI-09**: Portfolio heatmap (treemap) sizes positions by weight and colors them by P&L (green profit, red loss)
- [ ] **UI-10**: P&L chart plots total portfolio value over time from `/api/portfolio/history`
- [ ] **UI-11**: Collapsible AI chat panel with message input, scrolling history, a loading indicator while waiting, and inline confirmations of executed trades and watchlist changes
- [ ] **UI-12**: Portfolio, positions and charts refresh after manual or AI-executed trades
- [ ] **UI-13**: Layout is dense and desktop-first and remains functional at tablet width
- [ ] **UI-14**: UI elements expose the `data-testid` hooks used by the E2E suite

### Deployment (§3, §4, §11)

- [x] **OPS-01**: FastAPI serves the static frontend and all `/api/*` routes on port 8000 from one origin
- [x] **OPS-02**: `GET /api/health` returns healthy status for Docker and deployment checks
- [ ] **OPS-03**: Multi-stage Dockerfile builds the frontend (Node 20) and runs the backend (Python 3.14 + uv sync from lockfile)
- [ ] **OPS-04**: `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally` starts a working app
- [ ] **OPS-05**: `scripts/start_mac.sh` and `scripts/start_windows.ps1` build if needed (or on `--build`), run the container with volume, port and `.env`, and print the URL; they are idempotent
- [ ] **OPS-06**: `scripts/stop_mac.sh` and `scripts/stop_windows.ps1` stop and remove the container but keep the volume; they are idempotent
- [ ] **OPS-07**: `.env.example` documents `OPENROUTER_API_KEY`, `MASSIVE_API_KEY` and `LLM_MOCK`; `.env` is gitignored and read from the project root

### Testing (§12)

- [x] **TEST-01**: Backend pytest covers market data (valid simulator prices, GBM math, Massive parsing, interface conformance)
- [ ] **TEST-02**: Backend pytest covers portfolio logic (trades, P&L, oversell, insufficient cash, selling at a loss)
- [ ] **TEST-03**: Backend pytest covers LLM structured-output parsing, malformed responses and trade validation in the chat flow
- [ ] **TEST-04**: Backend pytest covers API routes (status codes, response shapes, errors)
- [ ] **TEST-05**: Frontend tests cover component rendering with mock data, price flash triggering, watchlist CRUD, portfolio calculations, and chat rendering with loading state
- [ ] **TEST-06**: `test/docker-compose.test.yml` runs the app container plus a Playwright container with `LLM_MOCK=true`
- [ ] **TEST-07**: E2E scenarios pass: fresh start, watchlist add/remove, buy, sell, portfolio visualization, mocked AI chat trade, SSE reconnection

## v2 Requirements

Deferred to a future release. Not in the current roadmap.

### Deployment

- **DEPLOY-01**: Terraform configuration for AWS App Runner in `deploy/` (PLAN.md stretch goal)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Login, signup, multi-user | Single-user by design; `user_id` columns keep the door open |
| Limit orders, order book, partial fills, fees, trade confirmation dialogs | Market orders only keep portfolio math simple |
| WebSockets | One-way SSE push is sufficient |
| Token-by-token LLM streaming | Cerebras is fast; a loading indicator suffices |
| Massive WebSocket feed | REST polling works on all tiers |
| Mobile-first layout | Desktop-first, functional on tablet |
| docker-compose orchestration for production | Single container; compose is an optional convenience only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MKT-01 | Phase 1 | Complete |
| MKT-02 | Phase 1 | Complete |
| MKT-03 | Phase 1 | Complete |
| MKT-04 | Phase 1 | Complete |
| MKT-05 | Phase 1 | Complete |
| MKT-06 | Phase 5 | Pending |
| MKT-07 | Phase 5 | Pending |
| MKT-08 | Phase 1 | Complete |
| MKT-09 | Phase 5 | Pending |
| STRM-01 | Phase 1 | Complete |
| STRM-02 | Phase 1 | Complete |
| STRM-03 | Phase 1 | Complete |
| STRM-04 | Phase 1 | Complete |
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 2 | Complete |
| DATA-04 | Phase 6 | Pending |
| PORT-01 | Phase 3 | Pending |
| PORT-02 | Phase 3 | Pending |
| PORT-03 | Phase 3 | Pending |
| PORT-04 | Phase 3 | Pending |
| PORT-05 | Phase 3 | Pending |
| PORT-06 | Phase 3 | Pending |
| PORT-07 | Phase 3 | Pending |
| PORT-08 | Phase 3 | Pending |
| WATCH-01 | Phase 2 | Complete |
| WATCH-02 | Phase 2 | Complete |
| WATCH-03 | Phase 2 | Complete |
| WATCH-04 | Phase 2 | Complete |
| CHAT-01 | Phase 4 | Pending |
| CHAT-02 | Phase 4 | Pending |
| CHAT-03 | Phase 4 | Pending |
| CHAT-04 | Phase 4 | Pending |
| CHAT-05 | Phase 4 | Pending |
| CHAT-06 | Phase 4 | Pending |
| CHAT-07 | Phase 4 | Pending |
| CHAT-08 | Phase 4 | Pending |
| CHAT-09 | Phase 4 | Pending |
| UI-01 | Phase 1 | Complete |
| UI-02 | Phase 3 | Pending |
| UI-03 | Phase 1 | Complete |
| UI-04 | Phase 1 | Complete |
| UI-05 | Phase 2 | Complete |
| UI-06 | Phase 2 | Pending |
| UI-07 | Phase 3 | Pending |
| UI-08 | Phase 3 | Pending |
| UI-09 | Phase 3 | Pending |
| UI-10 | Phase 3 | Pending |
| UI-11 | Phase 4 | Pending |
| UI-12 | Phase 3 | Pending |
| UI-13 | Phase 6 | Pending |
| UI-14 | Phase 6 | Pending |
| OPS-01 | Phase 1 | Complete |
| OPS-02 | Phase 1 | Complete |
| OPS-03 | Phase 6 | Pending |
| OPS-04 | Phase 6 | Pending |
| OPS-05 | Phase 6 | Pending |
| OPS-06 | Phase 6 | Pending |
| OPS-07 | Phase 6 | Pending |
| TEST-01 | Phase 1 | Complete |
| TEST-02 | Phase 3 | Pending |
| TEST-03 | Phase 4 | Pending |
| TEST-04 | Phase 6 | Pending |
| TEST-05 | Phase 6 | Pending |
| TEST-06 | Phase 6 | Pending |
| TEST-07 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 66 total
- Mapped to phases: 66
- Unmapped: 0

---
*Requirements defined: 2026-10-19*
*Last updated: 2026-10-19 after roadmap creation*
