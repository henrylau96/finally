---
phase: 03-trading-portfolio
plan: 01
subsystem: api
tags: [fastapi, sqlite, pydantic, nextjs, trading]
requires:
  - phase: 02
    provides: watchlist API, price cache, header/terminal shell
provides:
  - Atomic trade engine (execute_trade) and portfolio_view
  - POST /api/portfolio/trade and GET /api/portfolio
  - Header showing real cash and live total value
affects: [03-02, 03-03, 03-04, phase-4-ai-trades]
tech-stack:
  added: []
  patterns: [BEGIN IMMEDIATE transaction per trade, lifespan asyncio.Lock for trade serialization, shared Annotated validators]
key-files:
  created:
    - backend/app/portfolio.py
    - backend/app/api/schemas.py
    - backend/app/api/portfolio.py
    - backend/tests/test_portfolio.py
    - backend/tests/test_portfolio_api.py
    - frontend/src/lib/portfolio.ts
    - frontend/src/lib/usePortfolio.ts
  modified:
    - backend/app/main.py
    - backend/app/api/watchlist.py
    - backend/tests/conftest.py
    - frontend/src/components/Header.tsx
    - frontend/src/components/Terminal.tsx
    - test/e2e/helpers.ts
key-decisions:
  - "422 handler omits request input so NaN bodies return 422 instead of crashing serialization"
  - "Quantity rounded to 4 dp; avg_cost to 4 dp; cash to 2 dp"
requirements-completed: [PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, UI-02, TEST-02]
duration: 25min
completed: 2026-10-19
---

# Phase 3 Plan 01: Trade engine, portfolio API and live header Summary

Atomic market-order engine (BEGIN IMMEDIATE, weighted avg cost, fractional shares, sell-all deletes row) behind strict REST validation, with the header now showing real cash and a live SSE-marked total value.

## Tasks
1. Trade engine and portfolio view with 10 unit tests - e248572
2. REST API, shared Ticker/Quantity validators, lifespan trade lock, 24 API tests - e81e531
3. Frontend portfolio lib, usePortfolio hook, live Header, E2E helper wait - 25e9b38

Backend suite: 82 passed. Frontend lint/typecheck/build green. 01-fresh-start E2E: 3/3 on port 8014 (scratch DB, server stopped by PID).

## Deviations from Plan

**1. [Rule 1 - Bug] NaN quantity caused a 500 instead of 422**
- **Found during:** Task 2 (test_nan_quantity)
- **Issue:** FastAPI's default 422 body echoes the offending input; NaN cannot be serialized as JSON, raising ValueError.
- **Fix:** Added a RequestValidationError handler in main.py returning loc/msg/type only.
- **Files modified:** backend/app/main.py
- **Commit:** e81e531

**2. [Minor] Removed unused eslint-disable directive in usePortfolio.ts** (lint warning; the async refresh does not trip the rule).

## Known Stubs
None.

## Self-Check: PASSED
