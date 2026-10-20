---
phase: 05-real-market-data-massive
plan: 02
subsystem: market-data-ui
tags: [health, massive, sse, header, eod-badge]
requires: [MassiveDataSource.name, create_market_data_source]
provides: [MarketDataSource.name, create_health_router, usePriceStream asOf, header stale-badge]
affects: [backend/app/api/health.py, backend/app/main.py, frontend header, Playwright 01]
tech-stack:
  added: []
  patterns: [factory router taking the source, staleness computed in the SSE event handler (react-hooks/purity safe)]
key-files:
  created: []
  modified:
    - backend/app/market/interface.py
    - backend/app/market/simulator_source.py
    - backend/app/api/health.py
    - backend/app/main.py
    - backend/tests/test_health.py
    - frontend/src/lib/usePriceStream.ts
    - frontend/src/components/Header.tsx
    - frontend/src/components/Terminal.tsx
    - test/e2e/01-fresh-start.spec.ts
decisions:
  - "[05-02]: GET /api/health returns {status, source} with source = MarketDataSource.name"
  - "[05-02]: EOD badge shows when newest streamed timestamp is > 300 s old; date formatted in America/New_York"
metrics:
  duration: 15min
  completed: 2026-10-20
  tasks: 2
  files: 9
---

# Phase 5 Plan 02: Source Visibility and EOD Badge Summary

The health endpoint now reports which market data source is running. The header shows a muted `EOD · as of <NY date>` badge when the newest streamed price is more than 5 minutes old, so stale Massive data is never presented as live.

## What was built

- `MarketDataSource.name: str`. The simulator sets `name = "simulator"`. Massive already had `"massive"` from 05-01.
- `create_health_router(source)` returns `{"status": "ok", "source": source.name}`. `main.py` includes `create_health_router(source)`, and the old module-level router import is removed.
- `usePriceStream` keeps `asOf` state. It is set inside `es.onmessage` and never during render, so `react-hooks/purity` passes. It holds the newest timestamp when that timestamp is older than `STALE_SECONDS = 300`, and null otherwise. An empty payload gives null through the `Math.max(0, ...)` guard. The hook returns `asOf`.
- `Header` takes the `asOf` prop and renders `data-testid="stale-badge"` (`text-xs text-text-muted`). The date comes from a top-level `nyDate` helper using `toLocaleDateString("en-US", { timeZone: "America/New_York", ... })`. `Terminal` passes `asOf={asOf}`.
- Playwright 01 now asserts the health body `{ status: "ok", source: "simulator" }` and that there is no stale badge after prices update.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | 5eaba39 | failing health source tests |
| 1 (GREEN) | 362f964 | source name + create_health_router |
| 2 | a528207 | asOf hook state, header EOD badge, E2E 01 assertions |

## Verification

- `uv run pytest tests/test_health.py -q`: 2 passed. Full backend: 161 passed.
- Frontend `npm run lint`, `npm run typecheck` and `npm run build` all exit 0.
- Playwright 01 against a local simulator server on port 8032 (`MASSIVE_API_KEY=`, LLM_MOCK=true, scratch DB): 3 passed. The server was stopped by PID.
- `Date.now` does not appear in Header.tsx, and `asOf={asOf}` is in Terminal.tsx.

## TDD Gate Compliance

RED: 5eaba39 failed at collection with an ImportError for `create_health_router`. GREEN: 362f964.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED
