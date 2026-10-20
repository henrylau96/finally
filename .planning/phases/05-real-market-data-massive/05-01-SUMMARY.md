---
phase: 05-real-market-data-massive
plan: 01
subsystem: market-data
tags: [massive, polygon, market-data, sse, tdd]
requires: [PriceCache, MarketDataSource interface, app lifespan source.start]
provides: [MassiveDataSource, massive_parse helpers, env-driven factory, PriceCache reference close]
affects: [backend/app/market, backend/tests/conftest.py]
tech-stack:
  added: [massive 2.9.0]
  patterns: [injected SDK client with FakeClient tests, asyncio.to_thread for sync SDK calls]
key-files:
  created:
    - backend/app/market/massive_parse.py
    - backend/app/market/massive_source.py
    - backend/tests/market/test_massive_parse.py
    - backend/tests/market/test_massive_source.py
    - backend/tests/market/test_factory.py
  modified:
    - backend/app/market/cache.py
    - backend/app/market/factory.py
    - backend/app/market/__init__.py
    - backend/tests/conftest.py
    - backend/tests/market/test_cache.py
    - backend/pyproject.toml
    - backend/uv.lock
decisions:
  - "[05-01]: Massive source switches snapshot -> EOD once on NOT_AUTHORIZED; EOD interval >= 900 s; reference close = prev_day.close (snapshot) or bar.open (EOD)"
  - "[05-01]: conftest blanks MASSIVE_API_KEY before importing app.main so the suite always runs the simulator"
metrics:
  duration: 20min
  completed: 2026-10-20
  tasks: 3
  files: 12
---

# Phase 5 Plan 01: Massive Data Source Summary

I added a `MassiveDataSource` that takes an injected `RESTClient`. It polls `get_snapshot_all("stocks", ...)`. If the plan is not entitled to snapshots, it switches once to end-of-day grouped bars by New York date. Every quote goes into the shared `PriceCache` with its real source timestamp and a previous-close reference. The factory picks Massive when `MASSIVE_API_KEY` is non-empty after stripping whitespace.

## What was built

- `massive_parse.py` holds pure helpers:
  - `snapshot_quote` picks the price in this order: last_trade (ns) > minute bar (ms) > day close / prev close timed by `updated` (ns). It returns None when there is no timestamp.
  - `bar_quote` returns close, the bar time in seconds, and the open.
  - `latest_grouped_bars` steps back over a 403 or an empty day, at most 5 tries.
  - Also `not_authorized`, `NY` and `EOD_MIN_INTERVAL`.
- `massive_source.py`:
  - `start` runs a first poll that never raises.
  - The loop logs a failed poll and keeps going.
  - `add_ticker` prices a new ticker straight away. In snapshot mode it uses `get_snapshot_ticker`. In EOD mode it uses the cached grouped bar, or `get_previous_close_agg` if there is none. A ticker that is already tracked makes no client call.
  - `ny_today()` is a module-level function so tests can monkeypatch it.
- `PriceCache.update(..., reference=)` replaces the day-change base whenever a reference close is passed. Simulator callers don't pass one, so their behaviour is unchanged.
- `factory.py` reads `MASSIVE_API_KEY` (stripped) and `MASSIVE_POLL_INTERVAL` (default 15).
- `conftest.py` sets `os.environ["MASSIVE_API_KEY"] = ""` before `from app import main`. I checked that `main.source` is `SimulatorDataSource` under that setting.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | 7ff8838 | massive dependency, conftest key blanking, failing tests |
| 2 (GREEN) | 22c4a94 | parsing helpers + cache reference close |
| 3 (GREEN) | 26243a1 | MassiveDataSource + env-driven factory |

## Verification

- `uv run pytest tests/market -q`: 54 passed
- `uv run pytest -q` (full backend): 160 passed. No network calls; the FakeClient is the only client used.
- `time.time` appears 0 times in the Massive modules, and the `SnapshotMarketType` enum is not used.

## TDD Gate Compliance

RED: 7ff8838 (`test(05-01)`). The new modules failed at collection, and all 134 pre-existing tests passed. GREEN: 22c4a94 and 26243a1 (`feat(05-01)`). No refactor commit was needed.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED
