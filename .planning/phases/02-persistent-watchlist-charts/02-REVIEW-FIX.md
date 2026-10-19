---
phase: 02-persistent-watchlist-charts
fixed_at: 2026-10-19T00:00:00Z
review_path: .planning/phases/02-persistent-watchlist-charts/02-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-10-19
**Source review:** .planning/phases/02-persistent-watchlist-charts/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: Ticker validator accepts JSON null and booleans as tickers "NONE"/"TRUE"/"FALSE"

**Files modified:** `backend/app/api/watchlist.py`, `backend/tests/test_watchlist_api.py`
**Commit:** 21497f1
**Applied fix:** First added `None, True, False, 123` to the `test_invalid` parametrize list. This reproduced the bug: None, True and False returned 201. Then the `mode="before"` validator with `str(v)` became a default (after) validator, so pydantic's strict `str` check rejects non-strings with 422. Backend suite: 48 passed.

### WR-01: MainChart does not repaint history after the chart instance is recreated

**Files modified:** `frontend/src/components/MainChart.tsx`
**Commit:** c8a35ac
**Applied fix:** The chart-creation effect's cleanup now resets `shown.current = ""` and `lastTime.current = 0`, so the next sync pass calls `setData` with the full history. `""` matches the ref's initial value. Status: fixed, requires human verification (StrictMode remount behavior in `next dev`).

### WR-02: Concurrent watchlist reloads can apply a stale list

**Files modified:** `frontend/src/lib/useWatchlist.ts`
**Commit:** d13d1ef
**Applied fix:** Added a `seq` request-counter ref. `load()` ignores any response that is no longer the latest, so only the newest reload sets rows, error or loading. Status: fixed, requires human verification (race ordering logic).

---

_Fixed: 2026-10-19_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
