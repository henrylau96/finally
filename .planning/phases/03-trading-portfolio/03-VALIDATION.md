---
phase: 3
slug: trading-portfolio
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-19
---

# Phase 3 — Validation Strategy

> Per-phase validation contract. Source and full requirement-to-command map: `03-RESEARCH.md` "Validation Architecture" (authoritative; summarized here).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1 + pytest-asyncio (auto) + httpx ASGITransport; Playwright E2E; eslint + tsc + next build |
| **Config file** | `backend/pyproject.toml`, `test/playwright.config.ts` |
| **Quick run command** | `cd backend && ~/.local/bin/uv run pytest tests/test_portfolio.py tests/test_portfolio_api.py -x -q` |
| **Full suite command** | `cd backend && ~/.local/bin/uv run pytest -q && cd ../frontend && npm run lint && npm run typecheck && npm run build` |
| **Estimated runtime** | ~80 seconds |

---

## Sampling Rate

- **After every task commit:** quick pytest for the touched module; `npm run typecheck` for TS tasks
- **After every plan wave:** full suite command
- **Before `/gsd:verify-work`:** full suite plus Playwright 01 (first, fresh `DB_PATH`), 03, 04, and 02/06 regression on a scratch server
- **Max feedback latency:** 80 seconds

---

## Requirement Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| PORT-01 | portfolio shape, avg_cost fallback, totals | api | `uv run pytest tests/test_portfolio_api.py -k get_portfolio -x` | ❌ W0 | ⬜ pending |
| PORT-02 | buy fills at cache price, cash drops | api | `uv run pytest tests/test_portfolio_api.py -k buy -x` | ❌ W0 | ⬜ pending |
| PORT-03 | partial sell keeps avg; full sell deletes, position null | api | `uv run pytest tests/test_portfolio_api.py -k sell -x` | ❌ W0 | ⬜ pending |
| PORT-04 | fractional qty with 4 dp tolerance; weighted avg | unit | `uv run pytest tests/test_portfolio.py -k "avg or fractional" -x` | ❌ W0 | ⬜ pending |
| PORT-05 | oversell / insufficient cash -> 400, DB unchanged; loss sale cash correct | unit+api | `uv run pytest -k "oversell or insufficient or loss" -x` | ❌ W0 | ⬜ pending |
| PORT-06 | one trades row per success, none per failure | unit | `uv run pytest -k trade_log -x` | ❌ W0 | ⬜ pending |
| PORT-07 | snapshot at startup, after trade, and in 30 s loop (0.05 s in test); task cancelled on exit | api | `uv run pytest tests/test_snapshots.py -x` | ❌ W0 | ⬜ pending |
| PORT-08 | history <= 500 oldest-first | unit | `uv run pytest -k history_bounded -x` | ❌ W0 | ⬜ pending |
| (stream set) | watchlist ∪ positions; sold-out unwatched stops; failed unwatched trade stops | api | `uv run pytest tests/test_streaming_union.py -x` | ❌ W0 | ⬜ pending |
| (concurrency) | two concurrent buys exceeding cash -> exactly one 200 | api | `uv run pytest -k concurrent -x` | ❌ W0 | ⬜ pending |
| TEST-02 | all of the above | pytest | `cd backend && uv run pytest -q` | ❌ W0 | ⬜ pending |
| UI-02/07/08/12 | header values, trade bar, positions row, inline error | e2e | `cd test && WSLENV=BASE_URL BASE_URL=http://localhost:8014 npx playwright test e2e/01-fresh-start.spec.ts e2e/03-trading.spec.ts` | ✅ | ⬜ pending |
| UI-09/10 | heatmap `data-pnl`, P&L chart canvas and `data-points` | e2e | `cd test && WSLENV=BASE_URL BASE_URL=http://localhost:8014 npx playwright test e2e/04-portfolio-viz.spec.ts` | ✅ | ⬜ pending |
| UI (all) | lint, types, static build | static | `cd frontend && npm run lint && npm run typecheck && npm run build` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

E2E order: all specs share one DB. Run `01-fresh-start` first on a fresh `DB_PATH` (it asserts exactly 10000), then 03 and 04. Spec 05 is Phase 4. Servers: scratch `DB_PATH`, ports 8014+, stop by recorded PID (`pkill -INT -P $PID; kill -INT $PID`), never `pkill -f uvicorn`.

---

## Wave 0 Requirements

- [ ] `backend/tests/test_portfolio.py`, `test_portfolio_api.py`, `test_snapshots.py`, `test_streaming_union.py`
- [ ] `seed_position` helper in `backend/tests/conftest.py`; deterministic prices via `main.cache.update(...)` with the source stopped, or assert against the returned trade price
- [ ] `test/e2e/helpers.ts` `openApp` waits for `$` in `cash-balance`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Heatmap layout, colors and label hiding look right | UI-09 | Visual judgment | Buy 3-4 tickers of different sizes; check sizing and green/red intensity |
| P&L chart keeps growing from 30 s snapshots | UI-10, PORT-07 | Needs > 30 s of wall time | Leave the page open 2 minutes; points increase |
| Header total value ticks live | UI-02 | Visual | Hold a position; total value changes with prices |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 80s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
