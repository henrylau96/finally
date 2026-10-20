---
phase: 06-packaging-persistence-test-suite
plan: 09
subsystem: market-data
tags: [massive, throttle, history, gap-closure]
requires: []
provides:
  - Throttled single-flight MassiveDataSource.history
affects: [06-10]
tech-stack:
  added: []
  patterns: [asyncio.Lock plus monotonic spacing]
key-files:
  modified:
    - backend/app/market/massive_parse.py
    - backend/app/market/massive_source.py
    - backend/tests/market/test_massive_source.py
decisions:
  - Throttle inside the source; 15 s spacing in eod mode only
metrics:
  tasks: 1
  completed: 2026-10-20
requirements: [UI-03, MKT-01, TEST-04]
---

# Phase 6 Plan 09: Massive history throttle Summary

Massive history fetches in EOD mode are serialized by an asyncio.Lock and spaced HISTORY_SPACING (15 s) apart, single-flight per ticker, with an instant cache fast path.

## What changed
- `HISTORY_SPACING = 15` in massive_parse.py.
- `history` split into `_cached_history`, `_history_gap`, `_fetch_history`; cache checked before and inside `_history_lock`; `_last_history` set before each call so failures count against quota.
- Four new tests (spacing, single-flight, cache bypass, snapshot not throttled). Full backend suite: 187 passed.

## Deviations from Plan
- The RED run of the new tests timed out in a first-time `uv` environment build and was not observed failing; tests were written before the implementation and pass after it.

Commit: see git log (fix(06-09)).

## Self-Check: PASSED
