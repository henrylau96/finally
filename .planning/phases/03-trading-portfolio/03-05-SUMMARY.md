---
phase: 03-trading-portfolio
plan: 05
subsystem: ui
tags: [treemap, heatmap, react, tailwind]
requires:
  - phase: 03-04
    provides: derivePositions rows, Terminal layout
provides:
  - squarified treemap layout (no new dependency)
  - Heatmap panel sized by market value, colored by P&L, click to select
  - folded Phase 2 UI fixes (active panel underline, add-input refocus)
affects: [03-06]
tech-stack:
  added: []
  patterns: [ResizeObserver size hook, px geometry for label thresholds]
key-files:
  created:
    - frontend/src/lib/treemap.ts
    - frontend/src/lib/useSize.ts
    - frontend/src/components/Heatmap.tsx
  modified:
    - frontend/src/components/Terminal.tsx
    - frontend/src/components/Panel.tsx
    - frontend/src/components/Watchlist.tsx
    - frontend/src/components/WatchlistAddForm.tsx
key-decisions:
  - "Active panel underline is an inset box-shadow so the title strip stays 24px"
requirements-completed: [UI-09]
duration: 10min
completed: 2026-10-19
---

# Phase 3 Plan 5: Portfolio Heatmap Summary

Hand-built squarified treemap heatmap with P&L coloring, live SSE updates and click selection, plus the folded Phase 2 UI fixes.

## Tasks
1. Squarify, useSize, Heatmap panel, Terminal wiring: e8ff042
2. Active underline on Watchlist and Main chart, header alignment, add-input refocus on success and failure: f4ca4f1

## Verification
lint, typecheck, build green. Playwright on scratch server (port 8017, fresh DB): 01 (3), 03 and 04 (4), 02 and 06 (3) all passed. Server stopped by PID.

## Deviations from Plan
None. (Main chart `active` prop landed in the Task 1 commit because it shares Terminal.tsx with the heatmap wiring.)

## Self-Check: PASSED
