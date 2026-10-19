---
phase: 02-persistent-watchlist-charts
plan: 01
subsystem: database
tags: [sqlite, fastapi, watchlist, nextjs]
requires:
  - phase: 01-market-data-streaming
    provides: PriceCache, MarketDataSource add/remove_ticker, SSE stream, Terminal UI
provides:
  - SQLite schema (six PLAN.md tables) with lazy init and seed
  - Watchlist REST API (GET/POST/DELETE) driving DB, market source and cache
  - Browser watchlist rendered from GET /api/watchlist
affects: [02-02, 02-03, portfolio, chat]
tech-stack:
  added: []
  patterns: [connection-per-call sqlite via asyncio.to_thread, router factory taking cache and source]
key-files:
  created:
    - backend/db/schema.sql
    - backend/app/db.py
    - backend/app/api/watchlist.py
    - backend/tests/conftest.py
    - backend/tests/test_db.py
    - backend/tests/test_watchlist_api.py
    - frontend/src/lib/useWatchlist.ts
  modified:
    - backend/app/main.py
    - frontend/src/components/Terminal.tsx
    - frontend/src/components/Watchlist.tsx
    - .gitignore
  deleted:
    - frontend/src/lib/tickers.ts
key-decisions:
  - "Seed keyed off empty users_profile so an emptied watchlist is not reseeded on restart"
  - "users_profile keyed by id (default 'default') per PLAN.md"
  - "db functions take no path argument; they read DB_PATH at call time"
requirements-completed: [DATA-01, DATA-02, DATA-03, WATCH-01, WATCH-02, WATCH-03, WATCH-04]
duration: 20min
completed: 2026-10-19
---

# Phase 2 Plan 01: Persistent Watchlist API Summary

**SQLite-backed watchlist (six tables, lazy seed, WAL) with GET/POST/DELETE /api/watchlist driving the price stream, and a browser list rendered from the API instead of a hardcoded array.**

## Accomplishments
- init_db creates the DB file and parent dir, schema, 10000.0 cash profile and 10 default tickers; idempotent.
- API returns 201 on add, 200 on duplicate, 204/404 on delete, 422 on invalid tickers; add/remove update DB, source and cache.
- Removals and an empty watchlist persist across lifespan restarts.
- useWatchlist hook feeds Watchlist; Terminal sets `data-ticker` and falls back to the first row when the selection is missing.

## Task Commits
1. Task 1 (RED): 9837351 `test(02-01): add failing db and watchlist api tests`
2. Task 2 (GREEN): 435a678 `feat(02-01): sqlite watchlist with REST API driving the stream`
3. Task 3: 8e7ea6d `feat(02-01): render watchlist rows from the watchlist API`

## Verification
- Backend: 44 tests pass. Frontend lint, typecheck and build pass.
- Smoke on port 8011 with scratch DB: DB created, POST pypl 201, GET 11 rows ending in PYPL; server stopped by PID.

## Deviations from Plan
None. Minor: the smoke check was run step by step with a health poll instead of the single chained command.

## Known Stubs
Main chart panel still shows its placeholder text (plan 03 replaces it).

## Self-Check: PASSED
