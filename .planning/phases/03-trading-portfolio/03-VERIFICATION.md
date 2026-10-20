---
phase: 03-trading-portfolio
verified: 2026-10-19T12:10:00Z
status: passed
score: 5/5 roadmap success criteria verified
overrides_applied: 0
re_verification:
  previous_status: none
gaps: []
deferred: []
human_verification: []
---

# Phase 3: Trading & Portfolio Verification Report

**Phase Goal:** User buys and sells shares at market and watches portfolio value, positions and P&L update live
**Status:** passed (the human browser checkpoint in 03-06 was approved and is not re-requested)

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Trade bar buy/sell fills instantly at the current price, no confirmation; cash and positions update | VERIFIED | Live run on port 8021 (scratch DB): POST /api/portfolio/trade buy 0.5 AAPL filled at the cached 190.02, cash 9904.99. `TradeBar.tsx` calls `usePortfolio.trade`, which refreshes the portfolio. No confirm dialog. |
| 2 | Fractional quantities, avg cost on repeated buys, sell-all removes position | VERIFIED | Two 0.5 buys gave quantity 1.0 and avg 190.02. Selling 1 returned `position: null` and `positions: []`. `_next_position` computes the weighted average. `_write` deletes the row at qty <= EPS. |
| 3 | Insufficient cash or oversell shows an inline error and changes nothing | VERIFIED | Live: buying 100000 AAPL returned 400 "Insufficient cash..."; selling 5 with 1 held returned 400 "Cannot sell 5 AAPL; you hold 1". Cash and position were unchanged. `execute_trade` runs in a `BEGIN IMMEDIATE` transaction with rollback. `TradeBar` renders the error in `data-testid=trade-error`. |
| 4 | Header shows live total value, cash and connection dot | VERIFIED | `Header.tsx` renders `total-value`, `cash-balance` and `ConnectionStatus`. `Terminal.tsx` feeds total from `derivePositions(portfolio, quotes)`, so it is marked to the live SSE quotes. |
| 5 | Positions table, heatmap and P&L chart refresh after each trade; P&L chart keeps growing from 30s snapshots | VERIFIED | `usePortfolio.version` is bumped after a trade and drives `PnlChart`, which refetches /api/portfolio/history. `Heatmap` and `PositionsTable` take `positionRows`. `main.py` starts `snapshots.snapshot_loop` (30s interval, cancelled on shutdown) plus a startup snapshot. The trade route snapshots after each fill. Live history showed one snapshot per trade. |

**Score:** 5/5

## Requirements Coverage (all 15 IDs accounted for in ROADMAP and REQUIREMENTS.md, none orphaned)

| ID | Status | Evidence |
|----|--------|----------|
| PORT-01 | SATISFIED | GET /api/portfolio returns positions, cash, total_value and unrealized_pnl (live-checked). |
| PORT-02 | SATISFIED | POST /api/portfolio/trade buy fills at the cache price. |
| PORT-03 | SATISFIED | Sell works; selling all removes the position (live-checked). |
| PORT-04 | SATISFIED | Fractional quantities with a 4dp validator; avg cost verified. |
| PORT-05 | SATISFIED | 400 with a clear message; atomic rollback. |
| PORT-06 | SATISFIED | `_write` inserts into `trades` in the same transaction. |
| PORT-07 | SATISFIED | 30s `snapshot_loop`, startup snapshot, and a snapshot after each trade. |
| PORT-08 | SATISFIED | `snapshots.history(limit=500)` returns the most recent rows, oldest first (bounded). |
| UI-02 | SATISFIED | Header and ConnectionStatus. |
| UI-07 | SATISFIED | TradeBar with ticker, quantity, buy, sell and an inline error. |
| UI-08 | SATISFIED | PositionsTable (88 lines, fed by derived rows). |
| UI-09 | SATISFIED | Squarified treemap in `lib/treemap.ts` and `Heatmap.tsx`; fill and `data-pnl` come from `pnlState`. |
| UI-10 | SATISFIED | PnlChart (lightweight-charts) reads /api/portfolio/history. |
| UI-12 | SATISFIED | The `version` bump and refresh after a trade; the AI-trade path is a Phase 4 hook, and `refresh` is exposed. |
| TEST-02 | SATISFIED | `test_portfolio.py`, `test_portfolio_api.py` and `test_snapshots.py` exist and pass. |

## Behavioral Spot-Checks and Regression

| Check | Result |
|-------|--------|
| Full backend suite (`uv run pytest -q`) | 96 passed (includes Phase 1-2 market, streaming and watchlist tests) |
| Frontend `tsc --noEmit` and `eslint` | clean |
| SSE /api/stream/prices (live) | emits `data:` events with all tickers |
| GET /api/watchlist (live) | returns the 10 seeded tickers with prices |
| Server started on 8021 with a scratch DB | stopped by PID; no stray process |

## Anti-Patterns

No TBD/FIXME/XXX/TODO markers in `frontend/src` or `backend/app`. No stubs found: components are substantive, wired in `Terminal.tsx`, and fed by real data (DB, cache, SSE).

## Notes (non-blocking)

- `ChatDock` is a Phase 4 placeholder, which is expected.
- The 30s loop is exercised only via the unit tests in `test_snapshots.py`. I did not wait 30s live.
- The code review is pending in 03-REVIEW.md and was not consulted.

## Gaps Summary

None. The phase goal is achieved.

_Verified: 2026-10-19_
_Verifier: Claude (gsd-verifier)_
