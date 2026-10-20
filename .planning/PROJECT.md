# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a single-user, AI-powered trading workstation that streams live market data, lets the user trade a simulated $10,000 portfolio, and includes an LLM chat assistant that analyzes positions and executes trades and watchlist changes on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot, ships as one Docker container on port 8000, and is the capstone project of an agentic AI coding course, built entirely by coding agents.

## Core Value

From one command, the user lands in a live, dark trading terminal where prices stream, trades fill instantly, and the AI copilot can trade for them through chat.

## Requirements

### Validated

- ✓ GBM market simulator (correlated sectors, 2-5% shocks, realistic seeds) behind the `MarketDataSource` interface — Phase 1 (MKT-01..05)
- ✓ Shared in-memory price cache written by one background task — Phase 1 (MKT-08)
- ✓ SSE stream `GET /api/stream/prices` at ~500ms with auto-reconnect — Phase 1 (STRM-01..04)
- ✓ `GET /api/health` and FastAPI serving the Next.js static export from one origin — Phase 1 (OPS-01, OPS-02)
- ✓ Dark terminal shell with live watchlist: flashing prices, signed day change %, sparklines — Phase 1 (UI-01, UI-03, UI-04)

- ✓ SQLite database created and seeded at startup (six tables, $10,000 default user, 10 default tickers) — Phase 2 (DATA-01..03)
- ✓ Persistent watchlist API (list, add, remove, idempotent duplicate) driving what streams — Phase 2 (WATCH-01..04)
- ✓ Watchlist add/remove UI and Lightweight Charts main chart for the selected ticker — Phase 2 (UI-05, UI-06)

- ✓ Market-order trading with fractional shares, weighted avg cost and cash/share validation; append-only trade log — Phase 3 (PORT-01..06)
- ✓ Portfolio snapshots (startup, after trades, every 30 s) with bounded history; streamed set = watchlist ∪ positions — Phase 3 (PORT-07, PORT-08)
- ✓ Live header totals, trade bar, positions table, treemap heatmap and P&L chart refreshing after trades — Phase 3 (UI-02, UI-07..10, UI-12, TEST-02)

- ✓ AI chat copilot: LiteLLM -> OpenRouter gpt-oss-120b (Cerebras) with structured output, auto-executed trades and watchlist changes, persisted history, deterministic `LLM_MOCK` mode, non-blocking — Phase 4 (CHAT-01..09, TEST-03)
- ✓ Collapsible FinAlly AI chat dock with loading state, inline action chips and portfolio refresh — Phase 4 (UI-11)

- ✓ Optional Massive REST poller behind the same interface (snapshot with EOD fallback for free tier), env-selected source, true timestamps, instant price for new tickers — Phase 5 (MKT-06, MKT-07, MKT-09)

Validated in Phase 1: Live Price Terminal (2026-10-19). Validated in Phase 2: Persistent Watchlist & Charts (2026-10-19). Validated in Phase 3: Trading & Portfolio (2026-10-19). Validated in Phase 4: AI Chat Copilot (2026-10-20). Validated in Phase 5: Real Market Data (Massive) (2026-10-20).

### Active

The full specification is `planning/PLAN.md` (the source of truth). Summary:

- [ ] Market data: GBM simulator by default (~500ms ticks, correlated moves, random events, realistic seed prices) and a Massive (Polygon.io) REST poller when `MASSIVE_API_KEY` is set, behind one abstract interface
- [ ] Shared in-memory price cache (latest price, previous price, timestamp per ticker)
- [ ] SSE price stream at `GET /api/stream/prices` (~500ms cadence; ticker, price, previous price, timestamp, direction)
- [ ] SQLite at `db/finally.db`, lazily created and seeded (default user with $10,000 cash; 10 default tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX); every table has `user_id` defaulting to `"default"`
- [ ] Portfolio API: positions, cash, total value, unrealized P&L; market-order trades with instant fill (fractional shares, cash and share validation); portfolio history snapshots every 30s and after each trade
- [ ] Watchlist API: list with latest prices, add ticker, remove ticker
- [x] Chat API: LiteLLM -> OpenRouter `openrouter/openai/gpt-oss-120b` with Cerebras provider and structured outputs (`message`, `trades`, `watchlist_changes`); auto-executes actions; persists history; deterministic mock when `LLM_MOCK=true`
- [ ] Health check at `GET /api/health`
- [ ] Frontend (Next.js + TypeScript static export, Tailwind dark theme): watchlist with flashing prices and sparklines, main chart for the selected ticker, portfolio heatmap (treemap), P&L chart, positions table, trade bar, collapsible AI chat panel, header with live total value, cash and connection status dot
- [ ] FastAPI serves the static frontend and the API on one port
- [ ] Multi-stage Dockerfile (Node 20 -> Python 3.14 + uv), named volume for the database, idempotent start/stop scripts for macOS/Linux and Windows
- [ ] Tests: backend pytest unit tests, frontend component tests, Playwright E2E in `test/` with `docker-compose.test.yml` and `LLM_MOCK=true`

### Out of Scope

- Authentication, signup, multi-user — single user by design; `user_id` columns only keep the door open
- Limit orders, order book, partial fills, fees, confirmation dialogs — market orders only keep portfolio math simple
- WebSockets — one-way SSE push is enough
- Token-by-token LLM streaming — Cerebras is fast enough that a loading indicator suffices
- Massive WebSocket feeds — REST polling works on all tiers
- Cloud deployment (Terraform/App Runner in `deploy/`) — stretch goal, not core build
- Mobile-first layout — desktop-first, functional on tablet

## Context

- **Greenfield rebuild.** A previous implementation of the whole platform (built by a 6-agent team) was removed on branch `finally-gsd` (frontend in `4619f5b`, backend in `f2ef207`) so GSD can rebuild everything from `planning/PLAN.md`. It remains in git history; its codebase map is archived at `.planning/reference/codebase-prior/` for reference only. It does not describe the current tree.
- **Prior known issues worth not repeating:** Massive snapshot prices with missing timestamps looked live; adding a ticker on Massive gave it no starting price; the async chat handler did blocking sqlite calls; portfolio history was unbounded; the old `lib/` Python gitignore rule hid `frontend/src/lib`.
- **Remaining scaffolding** (may be reused or rewritten): `Dockerfile`, `docker-compose.yml`, `scripts/start_*`/`stop_*`, `test/` (Playwright config, `docker-compose.test.yml`, six E2E specs with `data-testid` hooks), `.env.example`, `db/.gitkeep`.
- **Reference docs:** `planning/MARKET_*.md`, `planning/MASSIVE_API.md`, `planning/archive/`, `planning/TEAM_CONTRACT.md`. The `cerebras` skill (`.claude/skills/cerebras`) shows how to call the LLM.
- **User's Massive key is free tier:** snapshots are NOT_AUTHORIZED, so real data runs in end-of-day mode (grouped daily bars, ~15 min polling).
- **Dev environment:** WSL2 on a `/mnt/c` checkout. uv at `~/.local/bin/uv`. WSL has no Node; Windows `node.exe` is used for tooling. Pushes go through Windows `git.exe` to the fork `henrylau96/finally` (local `origin` is upstream with no push access).

## Constraints

- **Tech stack**: FastAPI + uv (Python 3.14), Next.js TypeScript static export, Tailwind, SQLite, SSE, LiteLLM/OpenRouter/Cerebras — fixed by PLAN.md
- **Deployment**: single container, single port 8000, no CORS — students run one command
- **Tooling**: always `uv run` / `uv add`, never `python3` / `pip` — user rule
- **Code style**: simple, no over-engineering or defensive programming, short modules and functions, concise docstrings, no emojis, latest library APIs — user rule
- **Process**: work incrementally in small validated steps; identify and prove root cause before fixing — user rule
- **Visual**: dark theme (`#0d1117`/`#1a1a2e`, no pure black), accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991` for submit buttons; ~500ms price flash
- **Testing**: E2E runs with `LLM_MOCK=true` so it needs no API key

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Rebuild the entire project from scratch, including the backend | User wants GSD to deliver everything in PLAN.md end to end | — Pending |
| `planning/PLAN.md` is the source of truth for scope and done-criteria | User's explicit instruction | — Pending |
| SSE over WebSockets; static Next.js export; SQLite; single container | Simplicity, per PLAN.md section 3 | — Pending |
| LLM trades auto-execute without confirmation | Fake money, fluid agentic demo | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-20 after Phase 5*
