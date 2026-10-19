# Roadmap: FinAlly — AI Trading Workstation

## Overview

Vertical MVP: each phase ends with something the user can see and use in the browser. Phase 1 gets simulated prices streaming into a page served by FastAPI. Later phases add the persistent watchlist and charts, trading and portfolio visuals, the AI copilot, real market data, and finally packaging and the full test suite.

## Phases

- [x] **Phase 1: Live Price Terminal** - FastAPI serves a dark Next.js page where simulated prices stream into a flashing watchlist with sparklines (completed 2026-10-19)
- [ ] **Phase 2: Persistent Watchlist & Charts** - SQLite-backed watchlist the user can edit, with a main chart for the selected ticker
- [ ] **Phase 3: Trading & Portfolio** - Buy/sell at market, positions, heatmap, P&L chart and live header totals
- [ ] **Phase 4: AI Chat Copilot** - Chat panel where the LLM analyzes the portfolio and executes trades and watchlist changes
- [ ] **Phase 5: Real Market Data (Massive)** - Optional Massive REST poller behind the same interface, with correct timestamps and instant prices for new tickers
- [ ] **Phase 6: Packaging, Persistence & Test Suite** - One-command Docker run with persistent data, start/stop scripts, tablet-ready layout, unit and E2E tests

## Phase Details

### Phase 1: Live Price Terminal

**Goal**: User opens http://localhost:8000 and sees live simulated prices streaming into a dark terminal-style watchlist
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: MKT-01, MKT-02, MKT-03, MKT-04, MKT-05, MKT-08, STRM-01, STRM-02, STRM-03, STRM-04, OPS-01, OPS-02, UI-01, UI-03, UI-04, TEST-01
**Success Criteria** (what must be TRUE):

  1. Opening the app on port 8000 shows a dark-themed page (PLAN.md colors) served by FastAPI from one origin, and `GET /api/health` reports healthy
  2. Ticker rows show symbol, price, daily change % and a sparkline that fills in progressively from the SSE stream
  3. Prices update about every 500ms and flash green on upticks and red on downticks, fading over ~500ms
  4. Related tickers (e.g. tech stocks) visibly move together, with occasional sudden 2-5% jumps, starting from realistic prices
  5. After the backend restarts or the connection drops, the page resumes streaming without a manual reload

**Plans**: 5 plans

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Walking skeleton backend: GBM simulator -> PriceCache -> SSE stream, health, static mount (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Walking skeleton browser: Next.js static export with live ticker rows served from one origin (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Realistic market: Cholesky-correlated GBM, 2-5% shocks, seeds, MarketDataSource interface + factory, TEST-01 suite (wave 3)
- [x] 01-04-PLAN.md — Terminal UI: grid shell, connection dot states, flashing prices, Day %, sparklines (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-05-PLAN.md — Phase gate: documented local run, full suite + restart smoke, human browser verification (wave 4)

**UI hint**: yes

### Phase 2: Persistent Watchlist & Charts

**Goal**: User manages a persistent watchlist and inspects any ticker in a larger chart
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, WATCH-01, WATCH-02, WATCH-03, WATCH-04, UI-05, UI-06
**Success Criteria** (what must be TRUE):

  1. On a fresh start with no database file, the app creates and seeds `db/finally.db` and shows the 10 default tickers with $10,000 cash on record
  2. User can add a ticker from the watchlist panel and see it start streaming; adding a duplicate does not error or create a second row
  3. User can remove a ticker and it disappears and stops streaming, staying removed after a restart
  4. Clicking a ticker shows a larger price-over-time chart for it in the main chart area

**Plans**: TBD
**UI hint**: yes

### Phase 3: Trading & Portfolio

**Goal**: User buys and sells shares at market and watches portfolio value, positions and P&L update live
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, PORT-08, UI-02, UI-07, UI-08, UI-09, UI-10, UI-12, TEST-02
**Success Criteria** (what must be TRUE):

  1. User enters a ticker and quantity in the trade bar and clicks buy or sell; the order fills instantly at the current price with no confirmation, and cash and positions update
  2. Fractional quantities work, average cost updates correctly on repeated buys, and selling all shares removes the position
  3. A buy with insufficient cash or a sell above held shares shows an inline error and changes nothing
  4. The header shows live total value, cash balance and a connection dot (green, yellow, red)
  5. The positions table, treemap heatmap (green profit, red loss) and P&L chart refresh after each trade and the P&L chart keeps growing from 30-second snapshots

**Plans**: TBD
**UI hint**: yes

### Phase 4: AI Chat Copilot

**Goal**: User chats with FinAlly, which analyzes the portfolio and executes trades and watchlist changes on request
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09, UI-11, TEST-03
**Success Criteria** (what must be TRUE):

  1. User opens the collapsible chat panel, sends a message and sees a loading indicator and then a complete reply grounded in their cash, positions and watchlist
  2. Asking the AI to buy or sell executes the trade automatically and shows an inline confirmation; the portfolio views refresh to match
  3. Asking the AI to add or remove a ticker changes the watchlist and shows an inline confirmation
  4. A trade the AI attempts that fails validation (e.g. not enough cash) is explained in the reply and changes nothing
  5. With `LLM_MOCK=true` the chat returns a deterministic reply including a trade without an API key, and prices keep streaming during an LLM call
  6. Chat history persists across page reloads and malformed LLM output yields an error message rather than a crash

**Plans**: TBD
**UI hint**: yes

### Phase 5: Real Market Data (Massive)

**Goal**: User with a Massive API key gets real market data through the same pipeline as the simulator
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: MKT-06, MKT-07, MKT-09
**Success Criteria** (what must be TRUE):

  1. With `MASSIVE_API_KEY` set, the app streams real prices (free tier: end-of-day grouped bars polled about every 15 minutes) to the same UI; with it unset or empty the simulator runs
  2. Adding a ticker while on Massive gives it a price right away instead of waiting for the next poll
  3. Prices show their true source timestamp, so stale end-of-day data is not presented as live

**Plans**: TBD

### Phase 6: Packaging, Persistence & Test Suite

**Goal**: Anyone can start the whole app with one command, keep their data across restarts, and trust it via automated tests
**Mode:** mvp
**Depends on**: Phase 4, Phase 5
**Requirements**: DATA-04, OPS-03, OPS-04, OPS-05, OPS-06, OPS-07, UI-13, UI-14, TEST-04, TEST-05, TEST-06, TEST-07
**Success Criteria** (what must be TRUE):

  1. `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally` starts a working app built from the multi-stage Dockerfile
  2. The start script builds if needed (or on `--build`), runs the container and prints the URL; the stop script removes the container but keeps the volume; both are safe to run repeatedly on macOS/Linux and Windows
  3. After stopping and restarting the container, positions, cash, watchlist and chat history are still there
  4. The layout is dense on wide screens and remains usable at tablet width
  5. Backend route tests, frontend component tests and the Playwright E2E suite (fresh start, watchlist, buy, sell, visualizations, mocked AI trade, SSE reconnect) pass via `test/docker-compose.test.yml` with `LLM_MOCK=true`

**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Live Price Terminal | 5/5 | Complete    | 2026-10-19 |
| 2. Persistent Watchlist & Charts | 0/TBD | Not started | - |
| 3. Trading & Portfolio | 0/TBD | Not started | - |
| 4. AI Chat Copilot | 0/TBD | Not started | - |
| 5. Real Market Data (Massive) | 0/TBD | Not started | - |
| 6. Packaging, Persistence & Test Suite | 0/TBD | Not started | - |
