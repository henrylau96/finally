---
phase: 02-persistent-watchlist-charts
plan: 03
subsystem: ui
tags: [nextjs, lightweight-charts, sse, playwright]
requires:
  - phase: 02-persistent-watchlist-charts
    provides: Watchlist selection and Panel (plans 01, 02)
provides:
  - 1000-point per-ticker chart buffer in usePriceStream
  - MainChart Lightweight Charts 5.2.1 area chart with header and empty states
affects: []
tech-stack:
  added: [lightweight-charts@5.2.1]
  patterns: [single effect on [ticker, points]: setData+fitContent on ticker change, update() on ticks]
key-files:
  created:
    - frontend/src/components/MainChart.tsx
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/lib/usePriceStream.ts
    - frontend/src/components/Terminal.tsx
    - frontend/src/components/Panel.tsx
key-decisions:
  - "Ticker-switch and tick handling merged into one effect (a shown-ticker ref) because the react-hooks/refs lint rule forbids mirroring points into a ref during render"
requirements-completed: [UI-06]
duration: 12min
completed: 2026-10-19
---

# Phase 2 Plan 03: Main Chart Summary

**Clicking a watchlist ticker shows a live Lightweight Charts area chart (up to 1000 SSE points, no zoom reset on ticks) with ticker/price header and empty states.**

## Task Commits
1. Task 1: a62c0c1 `feat(02-03): add lightweight-charts and 1000-point chart buffer`
2. Task 2: 61faea9 `feat(02-03): live main chart for the selected ticker`

## Verification
- Lint, typecheck, static build pass without next/dynamic (top-level import works).
- Playwright 02-watchlist.spec.ts: 2 passed on port 8012 with a scratch DB; server stopped by PID.
- fitContent appears once in MainChart (ticker-switch branch).

## Deviations from Plan
**[Rule 3 - Blocking] Merged the two chart effects into one.** The plan's `[points]` effect needed the latest points inside the `[ticker]` effect, which required writing a ref during render and failed lint (react-hooks/refs). One `[ticker, points]` effect now does setData+fitContent when the ticker changes and update() otherwise. Behavior matches the plan.

The optional extra fitContent when a ticker reaches 2 points was not added; not observed as needed (no visual check beyond E2E).

## Known Stubs
Heatmap, Positions, P&L placeholders remain (later phases).

## Self-Check: PASSED
