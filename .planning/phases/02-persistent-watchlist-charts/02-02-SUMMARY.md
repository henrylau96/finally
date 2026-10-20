---
phase: 02-persistent-watchlist-charts
plan: 02
subsystem: ui
tags: [nextjs, watchlist, a11y, playwright]
requires:
  - phase: 02-persistent-watchlist-charts
    provides: Watchlist REST API and useWatchlist hook (plan 01)
provides:
  - Add-ticker form with client validation and inline errors
  - Per-row remove button
  - Watchlist as role=grid with fixed notice and error slots and empty state
affects: [02-03]
tech-stack:
  added: []
  patterns: [mutation hooks return error string or null, then reload]
key-files:
  created:
    - frontend/src/components/WatchlistAddForm.tsx
  modified:
    - frontend/src/lib/useWatchlist.ts
    - frontend/src/components/Watchlist.tsx
    - frontend/src/components/WatchlistRow.tsx
    - frontend/src/components/Terminal.tsx
    - frontend/src/components/Panel.tsx
    - frontend/src/app/globals.css
key-decisions:
  - "add/remove return an error message or null; the UI shows it in a reserved 24px alert slot"
requirements-completed: [UI-05, WATCH-02, WATCH-03, WATCH-04]
duration: 10min
completed: 2026-10-19
---

# Phase 2 Plan 02: Add/Remove Watchlist UI Summary

**Add-ticker form and per-row remove in the watchlist panel, with grid/aria-selected semantics, Space selection, fixed notice/error slots and an empty state.**

## Task Commits
1. Task 1: a383c6c `feat(02-02): add tickers from the watchlist panel`
2. Task 2: 28ee635 `feat(02-02): remove tickers, grid semantics and fixed notice slot`

## Verification
- Lint, typecheck, build pass.
- Playwright 02-watchlist.spec.ts: 2 passed on port 8011 with a scratch DB; server stopped by PID.

## Deviations from Plan
None.

## Known Stubs
Main chart panel placeholder remains (plan 03).

## Self-Check: PASSED
