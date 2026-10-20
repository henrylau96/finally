---
phase: 06-packaging-persistence-test-suite
plan: 03
subsystem: backend-tests
tags: [pytest, flaky-test, route-audit]
requires: []
provides:
  - deterministic seeded-cache test
  - route audit and smoke tests for remaining gaps
affects: [backend/tests]
key-files:
  created: [backend/tests/test_routes_smoke.py]
  modified: [backend/tests/market/test_source.py]
key-decisions:
  - "No HTTP test for GET /api/stream/prices: ASGITransport buffers the whole response and the SSE stream never ends; covered by tests/market/test_stream.py and Playwright 01/06"
requirements-completed: [TEST-04]
duration: long (slow uv/pytest startup on /mnt/c)
completed: 2026-10-20
---

# Phase 6 Plan 03: Backend route coverage and flaky test fix Summary

Fixed the racy seeded-cache test at its proven root cause and closed the remaining route-test gaps; full backend suite is 173 passed.

## Task 1: flaky test (ce3369f)

Root cause evidence (before the fix): with the `running` fixture, `cache.version` was 10 right after `start()` and 20 at the assertion point in 3/3 probe runs, so one simulator step (with a 0.1% per-ticker-per-step chance of a 2-5% shock) always ran before the 1% check. Looping the original test 30 times produced 1/30 failures. Fix: the test builds its own source, reads the cache with no `await` after `start()`, stops in `try/finally`. Tolerance unchanged (1%). After fix: 30/30 green.

## Task 2: route audit (02f847c)

| Route | Status codes asserted | Shape / test |
|---|---|---|
| GET /api/health | 200 | test_health.py |
| GET /api/portfolio | 200 | exact dict, test_portfolio_api.test_get_portfolio_fresh |
| GET /api/portfolio/history | 200 | keys total_value, recorded_at, test_snapshots.py |
| POST /api/portfolio/trade | 200, 400 (cash, oversell), 422 (incl. side "hold") | test_portfolio_api.py |
| GET /api/watchlist | 200 | test_watchlist_api.test_list |
| POST /api/watchlist | 201, 200 duplicate, 422 | test_watchlist_api.py |
| DELETE /api/watchlist/{ticker} | 204, 404 | test_watchlist_api.test_remove |
| POST /api/chat | 200 (mock + real path), 422 empty/whitespace/oversize (test_chat_mock.py); 422 + `detail`, `{}` body (new) | test_chat_api.py, test_routes_smoke.py |
| GET /api/chat/history | 200 | roles/actions (test_chat_store.py); full key set id, role, content, actions, created_at (new) |
| GET /api/stream/prices | n/a over HTTP | tests/market/test_stream.py; Playwright 01/06 |
| unknown /api path | 404 (new) | test_routes_smoke.py |

New tests: 422-with-detail for 4 bad chat bodies, chat history entry shape, unknown API path 404.

## Deviations from Plan

None. Note: I ran one empty `python3` heredoc by mistake (no-op, no effect).

## Self-Check: PASSED
