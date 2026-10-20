---
phase: 06-packaging-persistence-test-suite
plan: 06
subsystem: backend-market-data
tags: [history, massive, gap-closure]
requires: []
provides: [MarketDataSource.history, GET /api/history/{ticker}]
affects: [frontend MainChart seeding (plan 06-07)]
key-files:
  created: [backend/app/api/history.py, backend/tests/test_history_api.py]
  modified:
    - backend/app/market/interface.py
    - backend/app/market/simulator_source.py
    - backend/app/market/massive_parse.py
    - backend/app/market/massive_source.py
    - backend/app/main.py
    - backend/tests/market/test_interface.py
    - backend/tests/market/test_massive_parse.py
    - backend/tests/market/test_massive_source.py
decisions:
  - "History cached per ticker per NY day in memory; failures return [] uncached"
metrics:
  completed: 2026-10-20
requirements-completed: [UI-06, MKT-01, TEST-04]
---

# Phase 6 Plan 06: Daily history endpoint Summary

Source-agnostic `MarketDataSource.history(ticker)` (Massive: 180 days of daily closes via `get_aggs`, cached once per ticker per NY day; simulator: `[]`) exposed as `GET /api/history/{ticker}` with 422 on invalid tickers.

## Tasks

1. History on interface, parse helpers (`daily_points`, `history_window`), Massive and simulator implementations - 7f0fa3a
2. History router, registration in main.py, route tests - see second commit (feat(06-06): add GET /api/history/{ticker} route)

## Verification

Full backend suite: 183 passed (173 baseline + 10 new).

## Deviations from Plan

None - plan executed as written. The worktree was reset to the expected base commit 480dbb2 at start.

## Self-Check: PASSED
