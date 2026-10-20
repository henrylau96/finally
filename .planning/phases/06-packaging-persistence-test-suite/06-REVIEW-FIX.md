---
phase: 06-packaging-persistence-test-suite
fixed_at: 2026-10-20T08:55:00Z
review_path: .planning/phases/06-packaging-persistence-test-suite/06-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 5
skipped: 1
status: partial
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-10-20T08:55:00Z
**Source review:** .planning/phases/06-packaging-persistence-test-suite/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, WR-01 to WR-05; Info findings out of scope)
- Fixed: 5
- Skipped: 1

## Fixed Issues

### CR-01: The EOD history throttle ignores poll and add-ticker calls

**Files modified:** `backend/app/market/massive_parse.py`, `backend/app/market/massive_source.py`, `backend/tests/market/test_massive_parse.py`, `backend/tests/market/test_massive_source.py`
**Commit:** 45c97b2
**Status:** fixed: requires human verification (rate-limit logic)
**Applied fix:** All Massive requests now go through one `MassiveDataSource._call`. This covers snapshot_all, snapshot_ticker, previous_close, each grouped-daily attempt and get_aggs. In EOD mode it allows at most `EOD_CALLS = 5` calls in any `RATE_WINDOW = 61` s (a sliding window using a deque of call times). It is not unlimited in snapshot mode: calls are still recorded there, but no wait is applied. I used a sliding window instead of the review's fixed 15 s gap so startup is not blocked. A fixed gap would hold the lifespan start for up to 60 s on a Monday (5 grouped attempts), while the window lets the startup burst through and then spaces later calls. `latest_grouped_bars` now takes an async `fetch` callable so each grouped attempt is counted. `HISTORY_SPACING` and the history-only gap were removed. New test `test_eod_limit_counts_poll_and_add_ticker_calls` checks that poll, add-ticker and history calls share the limit. The existing throttle tests were adapted to the new constants.

### WR-01: `useHistorySeeds` caches failures as permanent empty seeds

**Files modified:** `frontend/src/lib/useHistorySeeds.ts`, `frontend/src/lib/useHistorySeeds.test.ts`
**Commit:** a23d4a0
**Applied fix:** Only successful responses are stored. A failed ticker goes into a `failed` list so the sequential loop moves on. When nothing else is left, the list clears after `RETRY_MS` (60 s), so failed tickers are fetched again without a page reload. The old test, which locked in `[]` being stored, was replaced with one using fake timers: the failure is not stored, the next ticker loads, and the failed ticker is refetched and stored after `RETRY_MS`.

### WR-02: At tablet widths the watchlist column is narrower than its grid tracks

**Files modified:** `frontend/src/components/Terminal.tsx`, `frontend/src/components/Watchlist.tsx`, `frontend/src/components/WatchlistRow.tsx`, `test/e2e/07-responsive.spec.ts`
**Commit:** 381b80d
**Applied fix:** Root cause confirmed in a browser first. Measured with Playwright against the pre-fix build (the app already running on port 8000, whose rows used the `72px_1fr_72px_72px_24px` tracks), the watchlist body overflowed by 84 px at 1024 px and by 106 px at 768 px. The overflowing elements were the Chart and remove columns. Fix: below `xl`, the row and header tracks are `56px_1fr_56px_64px_24px` with `gap-1`. The chart track stays 64 px because the Sparkline SVG is a fixed 64 px. The minimum width of the tablet and `lg` watchlist column went from 240px to 312px. Measured after the fix: body 310 px with scrollWidth 310 at both 1024 and 768, and the price track is 76 px so `$1,234.56` fits. I added a `watchlistFits` assertion to all four responsive E2E tests. All 4 pass when run locally against the fixed build.

### WR-03: The EOD/stale indicator disappears entirely below `lg`

**Files modified:** `frontend/src/components/Header.tsx`, `frontend/src/components/Header.test.tsx`
**Commit:** 757a517
**Applied fix:** Below `lg` the badge now shows a short `EOD` (`lg:hidden`), and the full `EOD · as of {date}` shows from `lg` up. The test now asserts that the short `EOD` element exists with `lg:hidden`. I confirmed this test fails on the pre-fix Header.

### WR-04: Chart time formatting is wrong for the new daily history points

**Files modified:** `frontend/src/lib/chartTheme.ts`, `frontend/src/lib/chartTheme.test.ts` (new)
**Commit:** ff40fe7
**Status:** fixed: requires human verification (behaviour change noted below)
**Applied fix:** Root cause shown with node: a bar at midnight New York (1760414400) formats as `13 Oct` in America/Los_Angeles but is the 14 Oct session. `day` and `clock` now format in America/New_York, matching the Header. A new `tickLabel` shows the year on `TickMarkType.Year`, and the crosshair (`crosshairLabel`) now shows date and time. New unit tests cover the NY day, the year tick and the crosshair label. Behaviour change: intraday clock labels on the main chart and the P&L chart are now in New York time, not the browser's local time. This keeps the date and time in one label in the same zone. Please confirm this is what you want.

## Skipped Issues

### WR-05: EOD live quotes and daily history likely use different bar timestamps

**File:** `backend/app/market/massive_parse.py:36-38,62-69`, `frontend/src/lib/chartPoints.ts:13-19`
**Reason:** Root cause not proven, so no fix was applied, as the project rules require. Neither the SDK nor the docs state when `get_aggs` day bars are stamped. The `massive` SDK docstrings only say "beginning date for the aggregate window", and `planning/MASSIVE_API.md` says "`t` is the window timestamp". The grouped-bar fixture `1760731200000` (16:00 ET) comes from an illustrative doc example, not a recorded response. The history fixtures (`1760400000000` etc.) are arbitrary. Nothing in the code or fixtures shows the two timestamps differ for the same session. To verify, compare `client.get_grouped_daily_aggs("2025-10-17")` AAPL `t` with `client.get_aggs("AAPL", 1, "day", "2025-10-17", "2025-10-17")[0].timestamp` using a real key (2 free-tier calls). If they differ, normalize both to the NY trading date as the review suggests.
**Original issue:** `mergePoints` and `sparklineValues` rely on the EOD live point having the same time as the last history point. If day bars are stamped at midnight ET and grouped bars at 16:00 ET, the chart and sparkline get a duplicate close for the same session.

## Verification

Run in the review-fix worktree after all fixes:
- `cd backend && uv run pytest -q`: 188 passed
- `cd frontend && npm test`: 10 files, 45 tests passed
- `npm run lint`: exit 0
- `npm run typecheck`: exit 0
- `npm run build`: exit 0 (static export)
- `test/e2e/07-responsive.spec.ts`: 4 passed, run locally against the fixed build (backend on port 8765, simulator, `LLM_MOCK=true`)

Notes:
- The worktree was created under `/mnt/c/Users/fulai/projects/` instead of `/tmp`, because the node/npm wrappers run Windows binaries and need a `/mnt/c` cwd.
- When running Playwright through the Windows wrapper, `BASE_URL` must be passed with `WSLENV=BASE_URL`. Without it the tests silently hit `localhost:8000`.

---

_Fixed: 2026-10-20T08:55:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
