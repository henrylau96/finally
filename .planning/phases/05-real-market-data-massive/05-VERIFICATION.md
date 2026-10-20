---
phase: 05-real-market-data-massive
verified: 2026-10-20T00:00:00Z
status: gaps_found
score: 2/3 roadmap truths verified (SC2 partial)
overrides_applied: 0
gaps:
  - truth: "Adding a ticker while on Massive gives it a price right away (SC2 / MKT-09)"
    status: partial
    reason: "CR-01 confirmed. On a free-tier key, if no tickers are tracked at start(), _poll_once returns early so _mode never flips from snapshot to eod. _fetch_one in snapshot mode calls get_snapshot_ticker, which raises NOT_AUTHORIZED; add_ticker catches and logs it, so no price is cached. place_trade then fails with no price, reconcile_stream removes the ticker again, and the state repeats permanently."
    artifacts:
      - path: "backend/app/market/massive_source.py"
        issue: "_fetch_one (snapshot branch) does not handle not_authorized(); the mode switch exists only in _poll_once, which early-returns on empty _tickers"
    missing:
      - "Extract an _enter_eod() helper (sets _mode='eod', raises _interval to EOD_MIN_INTERVAL); call it from _fetch_one on not_authorized and fall through to the bar / previous-close path"
      - "Test: start([]) with a client whose get_snapshot_ticker raises 403, then add_ticker returns a cached price"
---

# Phase 5: Real Market Data (Massive) Verification Report

**Phase Goal:** User with a Massive API key gets real market data through the same pipeline as the simulator
**Status:** gaps_found (one narrow, real defect; the rest of the phase is sound)
**Re-verification:** No, initial verification

## Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | With MASSIVE_API_KEY set the app streams real prices (free tier: EOD grouped bars ~15 min) to the same UI; unset/empty runs the simulator | VERIFIED | `factory.py` strips the key and returns `SimulatorDataSource` if empty, else `MassiveDataSource(cache, RESTClient(...), interval)`. `main.py` builds the source via the factory and passes it to the same routers and streaming. `_poll_once` falls back to `_poll_eod` on NOT_AUTHORIZED, with the interval floored at `EOD_MIN_INTERVAL`. 56 market and health tests pass (run by me). |
| 2 | Adding a ticker on Massive gives it a price right away | PARTIAL (FAILED in one reachable state) | `add_ticker` calls `_fetch_one` immediately, which works in snapshot mode, in EOD mode with a cached bar, and via `get_previous_close_agg`. It breaks in the CR-01 state described below. |
| 3 | Prices carry the true source timestamp; stale EOD data is not shown as live | VERIFIED | `_write` passes the source `timestamp` to `cache.update`. `Header.tsx` shows a `stale-badge` ("EOD · as of <NY date>") driven by the timestamp age in `usePriceStream.ts`. The label is misleading on paid plans outside market hours (IN-04, advisory). |

## CR-01 Adjudication: CONFIRMED against the code

- `_poll_once` begins with `if not self._tickers: return`. The only place `_mode` becomes `"eod"` is inside this method, in the `get_snapshot_all` except branch.
- `_fetch_one` in snapshot mode calls `get_snapshot_ticker` with no entitlement handling. `add_ticker` wraps it in `except Exception: logger.exception; return`, so the failure is swallowed and the cache stays empty.
- `services.place_trade` raises "No price available" (the review's trace). `reconcile_stream` then removes the ticker, so `_tickers` is empty again and the loop polls return early forever.
- Reachability: `main.py` calls `source.start(streaming.streamed_tickers())`, which is watchlist union positions. The default seed has 10 tickers, so the normal path hits the `start()` poll, flips to EOD and works. The broken state needs a free-tier key AND an empty watchlist with no positions at startup. A user can reach it by deleting every watchlist ticker and restarting. Once there, it never recovers until a ticker is persisted in the watchlist and the app restarts.
- Verdict: a goal-level gap against SC2 / MKT-09 in a narrow but reachable state, not merely advisory. The failure is permanent and silent, and the fix is small (about 10 lines plus one test). I did not run a live repro. Confirmed by code trace; the existing tests do not cover `start([])` with a 403 on single-snapshot.

## Requirements Coverage

| Requirement | Plans | Status | Evidence |
|-------------|-------|--------|----------|
| MKT-06 (key selects Massive, else simulator) | 05-01, 05-02, 05-03 | SATISFIED | `factory.py`, `test_factory.py`, health `source` field |
| MKT-07 (union of watched tickers, configurable interval, simulator-format parse) | 05-01, 05-03 | SATISFIED | `massive_source.py`, `massive_parse.py`, `MASSIVE_POLL_INTERVAL`, EOD floor |
| MKT-09 (instant price for new ticker, true timestamps) | 05-01, 05-02, 05-03 | PARTIAL | Timestamps are fine; instant price is broken in the CR-01 state |

No orphaned requirement IDs: REQUIREMENTS.md maps only MKT-06, MKT-07 and MKT-09 to Phase 5, and all three are claimed by plans.

## Other Review Findings (advisory, not goal blockers)

- WR-01: free-tier 5 calls/min can be exceeded at startup, and SDK retries add to it. A failed first EOD poll leaves the cache empty for 15 minutes.
- WR-02: `start()` awaits network I/O inside the lifespan, so startup and `/api/health` can block.
- WR-03: an invalid key logs a traceback every poll and health still says ok.
- WR-04: unchanged writes bump the cache version and add flat sparkline points.
- IN-01 to IN-05: minor.

WR-01 is the one to fix alongside CR-01, since it extends the same "no price, trades fail" window at startup.

## Anti-Patterns

No TBD/FIXME/XXX markers in `backend/app/market/*.py`.

## Spot-Checks

`uv run pytest tests/market tests/test_health.py` gives 56 passed. No probes are declared for this phase. I did not run live Massive calls and did not read .env.

## Human Verification

None required beyond the gap fix. Optionally, test with a real free-tier key once CR-01 is fixed.

## Gaps Summary

Phase 5 delivers the Massive source, factory selection, EOD fallback, true timestamps and the stale badge. One gap remains: CR-01, where a free-tier key starting with zero tracked tickers never switches to EOD mode, so newly added tickers get no price. Close it with a small gap-closure plan (fix CR-01, optionally WR-01).

---

_Verified: 2026-10-20_
_Verifier: Claude (gsd-verifier)_
