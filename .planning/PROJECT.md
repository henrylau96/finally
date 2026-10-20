# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a single-user, AI-powered trading workstation that streams live market data, lets the user trade a simulated $10,000 portfolio, and includes an LLM chat assistant that analyzes positions and executes trades and watchlist changes on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot, ships as one Docker container on port 8000, and is the capstone project of an agentic AI coding course, built entirely by coding agents.

## Core Value

From one command, the user lands in a live, dark trading terminal where prices stream, trades fill instantly, and the AI copilot can trade for them through chat.

## Current State

**v1.0 MVP shipped 2026-10-20** (tag `v1.0`). All of `planning/PLAN.md` is built:
- simulator and optional Massive market data
- SSE streaming
- SQLite persistence
- trading and portfolio visualizations
- the AI chat copilot
- one-command Docker packaging with a persistent volume
- backend, frontend and E2E test suites

See `.planning/MILESTONES.md` and `.planning/milestones/v1.0-*`.

## Requirements

### Validated

- ✓ GBM market simulator (correlated sectors, 2-5% shocks, realistic seeds) behind the `MarketDataSource` interface — v1.0 (MKT-01..05)
- ✓ Shared in-memory price cache written by one background task — v1.0 (MKT-08)
- ✓ SSE stream `GET /api/stream/prices` at ~500ms with auto-reconnect — v1.0 (STRM-01..04)
- ✓ `GET /api/health` and FastAPI serving the Next.js static export from one origin — v1.0 (OPS-01, OPS-02)
- ✓ Dark terminal shell with live watchlist: flashing prices, signed day change %, sparklines — v1.0 (UI-01, UI-03, UI-04)
- ✓ SQLite database created and seeded at startup (six tables, $10,000 default user, 10 default tickers) — v1.0 (DATA-01..03)
- ✓ Persistent watchlist API (list, add, remove, idempotent duplicate) driving what streams — v1.0 (WATCH-01..04)
- ✓ Watchlist add/remove UI and Lightweight Charts main chart for the selected ticker — v1.0 (UI-05, UI-06)
- ✓ Market-order trading with fractional shares, weighted avg cost and cash/share validation; append-only trade log — v1.0 (PORT-01..06)
- ✓ Portfolio snapshots (startup, after trades, every 30 s) with bounded history; streamed set = watchlist ∪ positions — v1.0 (PORT-07, PORT-08)
- ✓ Live header totals, trade bar, positions table, treemap heatmap and P&L chart refreshing after trades — v1.0 (UI-02, UI-07..10, UI-12, TEST-02)
- ✓ AI chat copilot:
  - LiteLLM -> OpenRouter gpt-oss-120b (Cerebras) with structured output
  - trades and watchlist changes auto-execute
  - chat history is persisted
  - deterministic `LLM_MOCK` mode; chat calls don't block the server
  - v1.0 (CHAT-01..09, TEST-03)
- ✓ Collapsible FinAlly AI chat dock with loading state, inline action chips and portfolio refresh — v1.0 (UI-11)
- ✓ Optional Massive REST poller behind the same interface:
  - snapshot with EOD fallback for the free tier
  - env-selected source, true timestamps, instant price for new tickers
  - daily history for charts and sparkline seeds, under one shared rate limiter
  - v1.0 (MKT-06, MKT-07, MKT-09)
- ✓ Data persists across container restarts on the `finally-data` volume — v1.0 (DATA-04)
- ✓ Multi-stage Dockerfile and idempotent start/stop scripts for macOS/Linux and Windows; secrets only via `--env-file` — v1.0 (OPS-03..07)
- ✓ Tablet-usable layout and complete E2E hooks — v1.0 (UI-13, UI-14)
- ✓ Test suites — v1.0 (TEST-04..07):
  - backend pytest (188)
  - frontend Vitest (45)
  - Playwright E2E via `test/docker-compose.test.yml` with `LLM_MOCK=true` (23)

### Active

None. The next milestone defines new requirements (`/gsd:new-milestone`).

Candidate follow-ups carried from the v1.0 audit:
- Settle WR-05: check whether live grouped-bar and daily history timestamps differ, using a real Massive key.
- Complete the Nyquist VALIDATION.md drafts.
- Surface snapshot failures instead of only logging them.
- Pin the `uv` base image.
- Optional cloud deployment (Terraform/App Runner).

### Out of Scope

- Authentication, signup, multi-user — single user by design; `user_id` columns only keep the door open
- Limit orders, order book, partial fills, fees, confirmation dialogs — market orders only keep portfolio math simple
- WebSockets — one-way SSE push proved sufficient in v1.0
- Token-by-token LLM streaming — Cerebras is fast enough that a loading indicator suffices
- Massive WebSocket feeds — REST polling works on all tiers, including the user's free tier (EOD mode)
- Cloud deployment (Terraform/App Runner in `deploy/`) — stretch goal, not core build
- Mobile-first layout — desktop-first, functional on tablet (verified at 768/1024 px)

## Context

- **Shipped v1.0** on branch `finally-gsd` as a from-scratch GSD rebuild of `planning/PLAN.md`:
  - about 3,500 lines of Python (backend) and 2,700 lines of TypeScript (frontend and E2E)
  - 203 commits over 2026-10-19 to 2026-10-20
- **Tech stack:**
  - backend: FastAPI + uv on Python 3.14, SQLite in WAL mode
  - frontend: Next.js static export, Tailwind, Lightweight Charts
  - LLM: LiteLLM -> OpenRouter/Cerebras
  - market data: massive SDK
  - tests: Vitest, Playwright
- **Previous implementation** (6-agent team build) remains in git history only; its codebase map is archived at `.planning/reference/codebase-prior/`.
- **User's Massive key is free tier:**
  - snapshots are NOT_AUTHORIZED, so real data runs in end-of-day mode (grouped daily bars)
  - all Massive calls are capped at 5 per 61 s
- **Known tech debt:** see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`
- **Dev environment:**
  - WSL2 on a `/mnt/c` checkout; uv at `~/.local/bin/uv`
  - node/npm/npx/docker and gsd-sdk are wrappers around Windows binaries, so cwd must be under `/mnt/c`
  - the Windows-side gsd-sdk cannot merge WSL worktrees; merge them with WSL git
  - Playwright through the Windows wrapper needs `WSLENV=BASE_URL` to pass `BASE_URL`
  - pushes go through Windows `git.exe` to the fork `henrylau96/finally`

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
| Rebuild the entire project from scratch, including the backend | User wants GSD to deliver everything in PLAN.md end to end | ✓ Good — v1.0 shipped all 66 requirements |
| `planning/PLAN.md` is the source of truth for scope and done-criteria | User's explicit instruction | ✓ Good |
| SSE over WebSockets; static Next.js export; SQLite; single container | Simplicity, per PLAN.md section 3 | ✓ Good — one port, one command |
| LLM trades auto-execute without confirmation | Fake money, fluid agentic demo | ✓ Good — same services and validation as manual trades |
| Vertical MVP slices; Massive deferred to Phase 5 | Ship the simulator path first | ✓ Good |
| Chat actions run through lock-owning shared services | One code path for REST and chat trades | ✓ Good |
| Massive switches snapshot -> EOD on NOT_AUTHORIZED | Free tier support | ✓ Good |
| One shared Massive rate limiter (5 per 61 s sliding window) in EOD mode | Free tier counts polls, add-ticker and history calls together | ✓ Good — replaced the history-only 15 s throttle after review |
| Chart times formatted in New York time | Daily bars are NY sessions; avoids off-by-one dates west of NY | ⚠️ Revisit if intraday local-time labels are preferred |

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
*Last updated: 2026-10-20 after v1.0 milestone*
