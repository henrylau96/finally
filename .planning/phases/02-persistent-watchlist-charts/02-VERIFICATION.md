---
phase: 02-persistent-watchlist-charts
verified: 2026-10-19T00:00:00Z
status: passed
score: 4/4 roadmap success criteria verified (9/9 requirements satisfied)
overrides_applied: 0
re_verification:
  previous_status: none
---

# Phase 2: Persistent Watchlist & Charts Verification Report

**Phase Goal:** User manages a persistent watchlist and inspects any ticker in a larger chart
**Status:** passed
**Re-verification:** No, initial verification

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Fresh start creates and seeds `db/finally.db`; 10 default tickers, $10,000 cash on record | VERIFIED | `app/db.py` `DEFAULT_DB = <repo>/db/finally.db`, `init_db` creates the file, schema and seed. Ran server on port 8015 with scratch `DB_PATH` and no file: `GET /api/watchlist` returned the 10 default tickers with live prices. `users_profile.cash_balance = 10000.0`. All 6 tables exist. `db/*.db` is gitignored. |
| 2 | Add ticker streams; duplicate does not error or create a second row | VERIFIED | `POST {"ticker":"pypl"}` returned 201 (normalized to PYPL) and PYPL appeared in `/api/stream/prices`. A second POST returned 200 with no new row (`INSERT OR IGNORE` plus UNIQUE constraint). List had 11 entries. |
| 3 | Remove ticker: disappears, stops streaming, stays removed after restart | VERIFIED | `DELETE /api/watchlist/AAPL` returned 204. AAPL was absent from the SSE stream afterwards (0 occurrences). After killing and restarting the server on the same DB, the list was 10 tickers with AAPL gone and PYPL present. Unknown ticker returns 404. |
| 4 | Clicking a ticker shows a larger price-over-time chart in the main chart area | VERIFIED | `WatchlistRow` onClick calls `onSelect`. `Terminal` holds `selected` and passes `chart[selected]` to `MainChart`, which builds a lightweight-charts AreaSeries (setData on ticker change, update on new points). `tsc --noEmit` is clean. The human approved the 02-04 browser checkpoint (add/remove, selection, chart, restart persistence). |

## Requirements Coverage

All 9 IDs in the PLAN frontmatter match the ROADMAP list and REQUIREMENTS.md (marked Complete, mapped to Phase 2). No orphaned requirements.

| Requirement | Plan | Status | Evidence |
|-------------|------|--------|----------|
| DATA-01 | 02-01, 02-04 | SATISFIED | `db.init_db` in lifespan creates the file and schema on a missing DB. Verified live. |
| DATA-02 | 02-01, 02-04 | SATISFIED | 6 tables created from `backend/db/schema.sql`. `tests/test_db.py` passes. |
| DATA-03 | 02-01, 02-04 | SATISFIED | Seed gives `default` cash 10000.0 and the 10 tickers. Verified live. |
| WATCH-01 | 02-01, 02-04 | SATISFIED | `GET /api/watchlist` merges rows with cached prices. |
| WATCH-02 | 02-01, 02-02, 02-04 | SATISFIED | POST adds the ticker and calls `source.add_ticker`. It streams. |
| WATCH-03 | 02-01, 02-02, 02-04 | SATISFIED | DELETE removes the row and calls `source.remove_ticker`. |
| WATCH-04 | 02-01, 02-02, 02-04 | SATISFIED | Duplicate POST returns 200 and creates no second row. |
| UI-05 | 02-02, 02-04 | SATISFIED | `WatchlistAddForm`, `WatchlistRow` remove, and `useWatchlist` add/remove are wired in `Terminal`. |
| UI-06 | 02-03, 02-04 | SATISFIED | `MainChart.tsx` is wired to the selected ticker with a 1000-point buffer. |

## Behavioral Spot-Checks and Regression (Phase 1)

| Check | Result | Status |
|-------|--------|--------|
| Backend suite `uv run pytest -q` (includes Phase 1 market/stream/health tests) | 44 passed | PASS |
| SSE `/api/stream/prices` streams events | PYPL events seen after add. AAPL absent after remove. | PASS |
| `/api/health` | `{"status":"ok"}` | PASS |
| Frontend `tsc --noEmit` | no errors | PASS |

Servers were stopped by explicit PID. Port 8000 was untouched.

## Anti-Patterns and Review Findings (02-REVIEW.md)

None of these blocks the goal. The review-fix pass is expected to address them.

| Item | Severity | Note |
|------|----------|------|
| CR-01: the `AddTicker` validator coerces JSON `null`/`true`/`false` to "NONE"/"TRUE"/"FALSE". The `mode="before"` `str(v)` is still in the code. | Warning (not a goal blocker) | Normal string input works, and non-string input is not a user path in the UI. It should be fixed before Phase 4, when LLM-supplied tickers arrive. |
| WR-01: `MainChart` `shown` ref is not reset when the chart is recreated (dev StrictMode). | Warning | Affects dev builds only. |
| WR-02: concurrent watchlist reloads can apply stale results. | Warning | Minor. |

No TBD/FIXME/XXX markers were checked beyond the review's coverage. The review reported none.

## Human Verification Required

None. The human already approved the 02-04 browser checkpoint, and nothing found contradicts it. Header cash and total value showing `--` is by design until Phase 3.

## Gaps Summary

No gaps. All four roadmap success criteria and all nine requirements are verified against the running code. Phase 1 behavior (simulator, SSE, health, tests) is unchanged. CR-01, WR-01 and WR-02 remain as noted for the review-fix pass.

---

_Verified: 2026-10-19_
_Verifier: Claude (gsd-verifier)_
