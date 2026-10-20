---
phase: 05-real-market-data-massive
verified: 2026-10-20T00:00:00Z
status: passed
score: 3/3 roadmap truths verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/3
  gaps_closed:
    - "Adding a ticker while on Massive gives it a price right away (CR-01)"
  gaps_remaining: []
  regressions: []
---

# Phase 5: Real Market Data (Massive) Verification Report

**Phase Goal:** User with a Massive API key gets real market data through the same pipeline as the simulator
**Status:** passed
**Re-verification:** Yes, after gap closure 05-04

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | With MASSIVE_API_KEY set the app streams real prices (free tier: EOD bars ~15 min) to the same UI; unset or empty runs the simulator | VERIFIED | `factory.py` selects the source; the same routers and streaming are used. Unchanged since the first pass, and the full suite passes. |
| 2 | Adding a ticker on Massive gives it a price right away | VERIFIED | CR-01 closed. `_fetch_one` (massive_source.py:79-95) catches `not_authorized` from `get_snapshot_ticker`, calls `_enter_eod()` and falls through to the cached bar or `get_previous_close_agg`. `_enter_eod` (97-101) is the only place that sets `_mode = "eod"` and is also called from `_poll_once`. Regression test `test_add_ticker_empty_start_falls_back_to_eod` (test_massive_source.py:160) exercises `start([])` plus a 403 and asserts a price of 70.0, mode `eod` and interval >= 900. |
| 3 | Prices carry the true source timestamp; stale EOD data is not shown as live | VERIFIED | `_write` passes the source timestamp to the cache. The `Header.tsx` stale badge is unchanged. |

**Score:** 3/3

## CR-01 Closure

Confirmed by reading the code. The earlier failure path (empty start, snapshot 403 swallowed in `add_ticker`, no price, trade fails, ticker removed) now flips to EOD on the first `add_ticker` and prices from the previous close. The mode persists after `reconcile_stream` removes the ticker, so later trades also work.

## Spot-Checks

`cd backend && uv run pytest -q` gives 162 passed (full backend suite, run by me). No probes are declared for this phase. I made no live Massive calls.

## Requirements Coverage

| Requirement | Plans | Status | Evidence |
|-------------|-------|--------|----------|
| MKT-06 | 05-01, 05-02, 05-03 | SATISFIED | factory.py, test_factory.py, health `source` field |
| MKT-07 | 05-01, 05-03 | SATISFIED | massive_source.py, massive_parse.py, `MASSIVE_POLL_INTERVAL`, EOD floor |
| MKT-09 | 05-01, 05-02, 05-03, 05-04 | SATISFIED | Instant price in all states, including the CR-01 state; true timestamps |

REQUIREMENTS.md maps only MKT-06, MKT-07 and MKT-09 to Phase 5, and all three are claimed by plans. No orphaned IDs.

## WR-05 Assessment (advisory, not a blocker)

`add_ticker` (massive_source.py:58-69) appends the ticker to `_tickers` before fetching. After a failed fetch (transient error or empty result), a second `add_ticker` returns early, so the ticker stays unpriced until the next poll (15 s in snapshot mode, up to 900 s in EOD mode). It does not block the phase goal:
- The roadmap criterion is "adding a ticker gives it a price right away". That holds on the normal path and in the CR-01 state. WR-05 applies only after a fetch that has already failed (a transient 5xx, a timeout or a rate limit).
- For a non-watched ticker such as a trade-only ticker, `reconcile_stream` removes it after the failed trade, so a retry works.
- For a watched ticker, the regular poll prices it. The window is bounded and the failure is not silent, because `logger.exception` records it.
- The fix is small (skip the fetch only when the ticker is tracked and priced, about 3 lines plus a test). I recommend folding it into the follow-up with WR-01 to WR-04.

## Other Advisory Findings

WR-01 (free-tier call budget and SDK retries), WR-02 (startup blocks on network I/O), WR-03 (an invalid key logs a traceback every poll and health still says ok), WR-04 (flat duplicate sparkline points), IN-01 to IN-06 (including IN-06, where one single-ticker 403 switches the source to EOD permanently). None breaks a roadmap success criterion. They are quality and hardening items.

## Anti-Patterns

No TBD, FIXME or XXX markers in `backend/app/market/`.

## Human Verification

None required. Optionally, smoke-test with a real free-tier Massive key.

---

_Verified: 2026-10-20_
_Verifier: Claude (gsd-verifier)_
