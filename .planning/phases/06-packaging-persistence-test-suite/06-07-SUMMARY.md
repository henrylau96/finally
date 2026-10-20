---
phase: 06-packaging-persistence-test-suite
plan: 07
subsystem: frontend
tags: [chart, lightweight-charts, massive, gap-closure]
requires:
  - phase: 06-06
    provides: GET /api/history/{ticker}
provides:
  - Main chart seeded from daily history, then live SSE points
affects: [MainChart, Terminal]
tech-stack:
  added: []
  patterns: [pure merge helper keeps series strictly ascending]
key-files:
  created:
    - frontend/src/lib/chartPoints.ts
    - frontend/src/lib/chartPoints.test.ts
    - frontend/src/lib/useHistory.ts
    - frontend/src/components/MainChart.test.tsx
  modified:
    - frontend/src/components/MainChart.tsx
    - frontend/src/components/Terminal.tsx
    - frontend/src/lib/chartTheme.ts
key-decisions:
  - "Overlay depends on merged (history + stream) length, so simulator behaviour is unchanged"
requirements-completed: [UI-06, TEST-05]
duration: 5min
completed: 2026-10-20
---

# Phase 6 Plan 07: Main chart history seeding Summary

Main chart now loads `/api/history/{ticker}` on selection and merges it with live SSE points via `mergePoints`, so Massive end-of-day data shows a line instead of the permanent "Collecting price data" overlay.

## Tasks
1. mergePoints + useHistory (TDD, 5 tests) - a6bb6fa
2. MainChart history prop, Terminal wiring, date-aware tick labels, 4 MainChart tests - a94af4a

## Verification
npm test (33 passed, up from 24), lint, typecheck, build all exit 0.

## Deviations from Plan
None - plan executed as written. Not verified against the live 06-06 endpoint (built in parallel); coded to the contract.

## Self-Check: PASSED
