---
phase: 06-packaging-persistence-test-suite
plan: 10
subsystem: frontend
tags: [sparkline, history, gap-closure]
requires: [06-07]
provides: [sparklineValues, useHistorySeeds]
affects: [Terminal, Watchlist]
key-files:
  created:
    - frontend/src/lib/useHistorySeeds.ts
    - frontend/src/lib/useHistorySeeds.test.ts
  modified:
    - frontend/src/lib/chartPoints.ts
    - frontend/src/lib/chartPoints.test.ts
    - frontend/src/components/Terminal.tsx
    - frontend/src/components/Watchlist.test.tsx
decisions:
  - "Seeds fetched strictly sequentially via a single effect keyed on tickers and seeds; failures store []"
metrics:
  completed: 2026-10-20
---

# Phase 6 Plan 10: Seeded watchlist sparklines Summary

Watchlist sparklines are seeded from the last 30 daily closes of /api/history, fetched one ticker at a time, so every row draws a line on Massive end-of-day data; the simulator path is unchanged.

## Commits
- 01b1223: sparklineValues helper and useHistorySeeds hook (with tests)
- Task 2 commit: Terminal wiring and Watchlist tests

## Verification
Frontend gate green: 42 tests pass (was 33), lint, typecheck and build exit 0. Sparkline.tsx, WatchlistRow.tsx, Watchlist.tsx, usePriceStream.ts, useHistory.ts and MainChart.tsx are untouched.

## Deviations from Plan
- The worktree base was not the expected commit, so it was reset to 4af8e41 as the startup check instructs. No other deviations.

## Known Stubs
None.

## Self-Check: PASSED
