---
phase: 05-real-market-data-massive
fixed_at: 2026-10-20T11:45:00+08:00
review_path: .planning/phases/05-real-market-data-massive/05-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 5: Code Review Fix Report

**Fixed at:** 2026-10-20T11:45:00+08:00
**Source review:** .planning/phases/05-real-market-data-massive/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (Warnings only; Info items are out of scope)
- Fixed: 5 (WR-01 and WR-02 are partial; see notes)
- Skipped: 0

Each fix started with a failing test or a reproduction. Backend suite: 167 passed (162 before, plus 5 new tests).

## Fixed Issues

### WR-01: Startup and EOD polls can go over the free-tier budget, and SDK retries make it worse

**Files modified:** `backend/app/market/factory.py`, `backend/tests/market/test_factory.py`
**Commit:** 08c5fed
**Applied fix:** `RESTClient(api_key=key, retries=0)`. Reproduced against a local server that always returns 429: with the defaults, one call sent 4 requests; with `retries=0` it sends 1. A 429 still raises `MaxRetryError`, not `BadResponse`. That is fine, because stepping back a day on a rate limit would be wrong anyway.
**Partial:** I did not add caching of the resolved trading day or a short retry after a failed first EOD poll. Both would add state and timing logic. That would be over-engineering now that retries no longer multiply the calls.

### WR-02: Lifespan blocks on Massive network I/O before the app serves

**Files modified:** `backend/app/market/factory.py`, `backend/tests/market/test_factory.py`
**Commit:** b4a4125
**Applied fix:** I applied the review's minimum fix: `connect_timeout=5.0, read_timeout=5.0`. Against a server that never responds, one call took 10.0 s before the change and 5.0 s after.
**Partial:** `start()` still makes its first poll inline. Moving that poll into the loop task would make the startup `record_snapshot` value positions at avg cost (the cache is still empty), which puts a wrong point on the P&L chart. So the worst-case startup block is now about 6 x 5 s instead of minutes, but it is not zero.

### WR-03: An invalid API key logs a traceback on every poll

**Files modified:** `backend/app/market/massive_source.py`, `backend/tests/market/test_massive_source.py`
**Commit:** 117afe6
**Applied fix:** I added a `_safe_poll()` helper, used by both `start()` and `_run_loop()`. It logs `BadResponse` as one line with `logger.error` and keeps `logger.exception` for unexpected errors. `add_ticker` does the same. I did not do the optional `last_error` in `/api/health`.

### WR-04: The cache version bumps on every poll, duplicating sparkline points

**Files modified:** `backend/app/market/massive_source.py`, `backend/tests/market/test_massive_source.py`
**Commit:** fc7a6b2
**Status:** fixed: requires human verification (logic change)
**Applied fix:** `_write` now skips the update when the cached price and timestamp match the new quote. The new test showed that a repeated EOD poll used to bump `cache.version`. The frontend `history` was not changed. Note that a quote with the same price and time but a different reference is also skipped.

### WR-05: A failed first fetch leaves a ticker tracked but unpriced

**Files modified:** `backend/app/market/massive_source.py`, `backend/tests/market/test_massive_source.py`
**Commit:** db60d80
**Status:** fixed: requires human verification (logic change)
**Applied fix:** `add_ticker` now tracks the ticker if needed and skips the fetch only when the ticker is already priced. New test: a failing fetch, then a working client, then a second `add_ticker` prices the ticker (this failed before the fix). I updated `test_add_ticker_tracked_is_noop` so its ticker is priced, which matches the new contract.

---

_Fixed: 2026-10-20T11:45:00+08:00_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
