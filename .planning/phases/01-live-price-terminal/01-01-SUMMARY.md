---
phase: 01-live-price-terminal
plan: 01
subsystem: api
tags: [fastapi, sse, gbm, numpy, uv, pytest]

requires: []
provides:
  - backend uv project (Python 3.14) with locked deps
  - PriceCache / PriceUpdate six-key contract
  - GBMSimulator (uncorrelated) and SimulatorDataSource background task
  - GET /api/stream/prices native FastAPI SSE (retry 1000, ~500ms)
  - GET /api/health and static mount at / (STATIC_DIR)
affects: [01-02, 01-03, 01-04, 01-05]

tech-stack:
  added: [fastapi, uvicorn, numpy, pytest, pytest-asyncio, httpx]
  patterns:
    - "Cache version counter drives SSE change detection"
    - "SSE logic tested via the price_events generator, not HTTP"

key-files:
  created:
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/app/main.py
    - backend/app/market/ (models, cache, seed_prices, simulator, simulator_source)
    - backend/app/api/ (health, stream)
    - backend/tests/
  modified: []

key-decisions:
  - "Dropped change/change_percent from PriceUpdate.to_dict; day_change_pct vs session open only"
  - "main.py creates STATIC_DIR if missing because StaticFiles check_dir=False still raises per request"

requirements-completed: [MKT-02, MKT-08, STRM-01, STRM-02, STRM-03, OPS-01, OPS-02]

duration: 25min
completed: 2026-10-19
---

# Phase 1 Plan 01: Backend Price Stream Summary

**FastAPI backend streaming GBM-simulated prices for 10 tickers over native SSE from a shared in-memory cache, with health endpoint and static mount.**

## Accomplishments
- uv project with locked deps and pytest config; 12 tests green (cache, stream generator, health, simulator).
- Smoke on port 8010: health `{"status":"ok"}`, `text/event-stream`, `retry: 1000`, 8 frames in 4 s, 10-ticker six-key frame, 404 on unknown path, exit about 3 s after SIGINT with an SSE client attached.

## Task Commits
1. Task 1 (RED tests + scaffold): a9a6985
2. Task 2 (implementation): cb92794

## Deviations from Plan

**1. [Rule 1 - Bug] Unknown path returned 500 when static dir missing**
- **Found during:** Task 2 smoke
- **Issue:** Starlette `StaticFiles.check_config` raises RuntimeError on each request when the directory does not exist, even with `check_dir=False`; `/api/nope` gave 500 instead of 404.
- **Fix:** `STATIC_DIR.mkdir(parents=True, exist_ok=True)` before the mount (`backend/static` is gitignored).
- **Files modified:** backend/app/main.py
- **Commit:** cb92794

## Known Stubs
None. Correlation (Cholesky) and shock events default off here; plan 01-03 adds them as scoped.

## Issues Encountered
First smoke attempt hit the server before startup finished (slow /mnt/c); rerun passed.

## Self-Check: PASSED
