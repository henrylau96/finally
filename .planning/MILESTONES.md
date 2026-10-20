# Milestones

## v1.0 MVP (Shipped: 2026-10-20)

**Delivered:** A single-container AI trading workstation. Prices stream live, trades fill instantly against a simulated $10k portfolio, and an LLM copilot trades and edits the watchlist through chat.

**Phases completed:** 6 phases, 34 plans (Phases 1-6)

**Key accomplishments:**

- Live price terminal:
  - Cholesky-correlated GBM simulator with rare 2-5% shocks behind an abstract `MarketDataSource`.
  - Prices stream over SSE to a dark Next.js terminal with flashing prices, sparklines and a connection indicator.
- Persistent SQLite watchlist (lazy init and seed, WAL) with GET/POST/DELETE `/api/watchlist` driving the stream, plus a Lightweight Charts main chart.
- Market-order trading:
  - Cash and share validation.
  - Positions table, P&L treemap heatmap, and a portfolio value chart fed by snapshots taken every 30 s and after each trade.
- FinAlly AI copilot:
  - LiteLLM -> OpenRouter (Cerebras) with structured outputs.
  - Trades and watchlist changes auto-execute through the same services as the REST routes, shown inline in a chat dock.
  - `LLM_MOCK` gives deterministic tests.
- Optional real market data from Massive (Polygon):
  - REST polling with snapshot and EOD modes.
  - Daily history for the main chart and sparkline seeds.
  - One shared rate limiter for the free tier.
- One-command packaging:
  - Multi-stage Dockerfile, start/stop scripts for macOS and Windows, and a named volume for persistence.
  - Tablet layout.
  - Test suites: 188 backend pytest, 45 Vitest, and 23 Playwright E2E tests via docker compose.

**Stats:**

- 203 commits, 2026-10-19 -> 2026-10-20
- 118 files changed in backend/frontend/test/scripts, about 3,500 lines of Python and 2,700 lines of TypeScript
- 66/66 v1 requirements satisfied; audit status tech_debt (no blockers)

**Known deferred items at close:** 2. Both are audit-tool false positives and both are actually done (see STATE.md Deferred Items).

**Tech debt carried forward** (see milestones/v1.0-MILESTONE-AUDIT.md):

- WR-05: possible timestamp mismatch between live grouped bars and daily history bars. Unproven; needs a 2-call check with a real Massive key.
- All six VALIDATION.md files are still drafts (Nyquist partial).
- Snapshot failures are only logged.
- Phase 6 review info items IN-01..04 and IN-06.
- Base image pins `uv:latest`, which is unpinned.

---
