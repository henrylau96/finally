---
phase: 01-live-price-terminal
plan: 03
subsystem: api
tags: [gbm, cholesky, numpy, abc, factory, pytest]

requires:
  - phase: 01-live-price-terminal
    provides: PriceCache, GBMSimulator, SimulatorDataSource, SSE stream (plan 01)
provides:
  - Correlated GBM (Cholesky) with 2-5% shock events and dynamic add/remove ticker
  - MarketDataSource ABC and create_market_data_source factory wired into main.py
  - Backend market test suite (27 tests)
affects: [01-04, 01-05, phase-2, phase-5]

tech-stack:
  added: []
  patterns:
    - "Pair-rule correlation matrix -> np.linalg.cholesky, rebuilt on ticker add/remove"
    - "Source chosen via factory; cache and SSE stay source-agnostic"

key-files:
  created:
    - backend/app/market/interface.py
    - backend/app/market/factory.py
    - backend/tests/market/test_interface.py
    - backend/tests/market/test_source.py
  modified:
    - backend/app/market/simulator.py
    - backend/app/market/simulator_source.py
    - backend/app/market/__init__.py
    - backend/app/main.py
    - backend/tests/market/test_simulator.py

key-decisions:
  - "Factory always returns the simulator; MASSIVE_API_KEY selection deferred to Phase 5 (MKT-06)"

requirements-completed: [MKT-01, MKT-02, MKT-03, MKT-04, MKT-05, MKT-08, TEST-01]

duration: 15min
completed: 2026-10-19
---

# Phase 1 Plan 03: Correlated Simulator and Market Interface Summary

**Cholesky-correlated GBM with rare 2-5% shocks and realistic seeds, behind an abstract MarketDataSource chosen by a factory.**

## Accomplishments
- Seeded statistical tests confirm log-return moments, correlations (tech 0.6, finance 0.5, cross 0.3, TSLA 0.3 within 0.05), shock size bounds and add/remove ticker.
- Source lifecycle tests: cache seeded at start, loop updates, add/remove, double stop, loop survives a step exception.
- Full backend suite: 27 passed. Smoke on port 8011 through the factory: 6 data frames in 3 s; server stopped afterwards.

## Task Commits
1. Task 1 RED: 5817c44; GREEN: f185ffd
2. Task 2 RED: 049dd5f; GREEN: 585cf5a

## Deviations from Plan

**1. [Rule 1 - Test fix] Statistical tests need events disabled**
- The new default `event_probability=0.001` made shocks pollute the 20000-step moment/correlation tests; they now pass `event_probability=0.0` explicitly (as the plan behavior specified).

**2. [Rule 1 - Test fix] Seeding assertion relaxed**
- The async fixture yields to the loop, so the cache may already have ticked once; the test asserts all 10 tickers present and within 1% of seed rather than exact equality.

## Known Stubs
None.

## Issues Encountered
None beyond the above; slow /mnt/c startup handled with an 8 s wait.

## Self-Check: PASSED
