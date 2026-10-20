---
phase: 05-real-market-data-massive
plan: 04
subsystem: market-data
tags: [massive, eod-fallback, gap-closure]
requires: [05-01]
provides:
  - "MassiveDataSource._enter_eod single EOD switch, used by _poll_once and _fetch_one"
affects: [backend/app/market/massive_source.py]
key-files:
  modified:
    - backend/app/market/massive_source.py
    - backend/tests/market/test_massive_source.py
key-decisions:
  - "_enter_eod() is the only place that sets mode to eod; _fetch_one falls through to bar / previous-close path after it"
requirements-completed: [MKT-09]
duration: 5min
completed: 2026-10-20
---

# Phase 5 Plan 04: CR-01 EOD fallback on single-snapshot 403 Summary

A free-tier Massive key started with zero tickers now switches to EOD mode when `get_snapshot_ticker` returns NOT_AUTHORIZED, so a newly added ticker is priced immediately.

## Evidence

RED (commit 23df4cc): new test failed on unmodified code. The log showed `Massive fetch failed for PYPL` with `BadResponse NOT_AUTHORIZED` raised from `_fetch_one` line 82 (`get_snapshot_ticker`), swallowed by `add_ticker`, leaving no cache entry.

GREEN: `uv run pytest tests/market tests/test_health.py -q` gives 57 passed.

## Tasks

1. Regression test `test_add_ticker_empty_start_falls_back_to_eod` (RED) - 23df4cc
2. `_enter_eod()` helper; `_fetch_one` catches not_authorized and falls through; other errors re-raise (GREEN) - 2de7cc8

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED
