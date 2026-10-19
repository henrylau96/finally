---
phase: 03-trading-portfolio
plan: 03
subsystem: api
tags: [fastapi, streaming, market-data]
requires:
  - phase: 03-01
    provides: trade route, trade_lock, seed_position fixture
provides:
  - streamed set equals watchlist union held positions
  - reconcile_stream as the only app-level caller of source.remove_ticker
affects: [03-04, 03-05]
tech-stack:
  added: []
  patterns: [reconcile in finally after request work]
key-files:
  created:
    - backend/app/streaming.py
    - backend/tests/test_streaming_union.py
  modified:
    - backend/app/main.py
    - backend/app/api/portfolio.py
    - backend/app/api/watchlist.py
key-decisions:
  - "Trade route reconciles in a finally wrapping the add_ticker call too, so failed trades on unwatched tickers do not keep streaming"
requirements-completed: [PORT-03, TEST-02]
duration: 8min
completed: 2026-10-19
---

# Phase 3 Plan 03: Streamed set union Summary

Held tickers now stream from startup and after watchlist removal; sold-out or failed-trade unwatched tickers stop streaming via a single `reconcile_stream`.

## Tasks
1. streaming.py and startup union - 6a2c9dd
2. Reconcile after trades and watchlist removals - 2ab8bcb

Verification: full backend suite 90 passed.

## Deviations from Plan
None. The try/finally also wraps the initial add_ticker so a failure there still reconciles.

## Known Stubs
None.

## Self-Check: PASSED
