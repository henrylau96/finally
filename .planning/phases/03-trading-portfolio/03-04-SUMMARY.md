---
phase: 03-trading-portfolio
plan: 04
subsystem: api
tags: [fastapi, sqlite, lightweight-charts, snapshots]
requires:
  - phase: 03-02
    provides: usePortfolio version counter, Terminal layout
  - phase: 03-03
    provides: trade route reconcile_stream, lifespan
provides:
  - portfolio snapshots at startup, after trades, every 30 s
  - GET /api/portfolio/history bounded to 500 oldest-first
  - P&L line chart panel with dashed 10,000 baseline
  - shared chartTheme (createBaseChart, CHART) used by both charts
affects: [03-05]
tech-stack:
  added: []
  patterns: [rowid-bounded history subquery, seq-guarded refetch on version]
key-files:
  created:
    - backend/app/snapshots.py
    - backend/tests/test_snapshots.py
    - frontend/src/lib/chartTheme.ts
    - frontend/src/components/PnlChart.tsx
  modified:
    - backend/app/main.py
    - backend/app/api/portfolio.py
    - frontend/src/lib/portfolio.ts
    - frontend/src/components/MainChart.tsx
    - frontend/src/components/Terminal.tsx
key-decisions:
  - "pnl-chart test id and data-points sit on the P&L Panel section; canvas host inside it"
requirements-completed: [PORT-07, PORT-08, UI-10, UI-12, TEST-02]
duration: 15min
completed: 2026-10-19
---

# Phase 3 Plan 4: Portfolio History Summary

Snapshot recording (startup, post-trade, 30 s loop cancelled on shutdown), a rowid-bounded history endpoint, and a Lightweight Charts P&L panel sharing a chart theme with the main chart.

## Task Commits
- RED tests: 27e224a
- Task 1 (snapshots, history, lifespan): 1ddb894
- Task 2 (chart theme, PnlChart): d12302d

## Verification
- Backend: 96 tests pass (6 new in test_snapshots.py)
- Frontend lint, typecheck, build pass; E2E 01 and 03 pass on port 8016; history had 1 row on fresh server; server stopped by PID.

## Deviations from Plan
None - plan executed as written.

## Known Stubs
Heatmap panel remains a placeholder (plan 03-05).

## Self-Check: PASSED
