---
phase: 03-trading-portfolio
plan: 02
subsystem: ui
tags: [nextjs, react, trading]
requires:
  - phase: 03-01
    provides: trade and portfolio API, usePortfolio, derivePositions
provides:
  - Trade bar with client validation and inline errors
  - Positions table with live P&L
  - Shared ticker selection across watchlist, positions and trade bar
affects: [03-03, 03-04, 03-05]
tech-stack:
  added: []
  patterns: [trade() returns string | null error like useWatchlist mutations]
key-files:
  created:
    - frontend/src/components/TradeBar.tsx
    - frontend/src/components/PositionsTable.tsx
  modified:
    - frontend/src/lib/format.ts
    - frontend/src/lib/usePortfolio.ts
    - frontend/src/components/Terminal.tsx
key-decisions:
  - "Positions price cell uses test id price-pos-{TICKER} to avoid colliding with the watchlist price-{TICKER}"
requirements-completed: [UI-07, UI-08, UI-12]
duration: 15min
completed: 2026-10-19
---

# Phase 3 Plan 02: Trade bar and positions table Summary

Users can buy and sell from the browser with inline validation and server errors, see live-marked positions, and select a ticker from watchlist or positions to prefill the trade bar.

## Tasks
1. Trade bar, format helpers, usePortfolio.trade - 9ef1d6a
2. PositionsTable, Terminal layout and selection - 6af6b7f

Verification: lint, typecheck, build green. E2E on fresh scratch DB (port 8015, stopped by PID): 01-fresh-start 3/3, then 03-trading 3/3 and 02-watchlist 2/2.

## Deviations from Plan
None. usePortfolio.refresh already bumps version, so trade() also calls setVersion as specified (double bump is harmless).

## Known Stubs
Heatmap and P&L panels remain placeholders by design (03-04, 03-05).

## Self-Check: PASSED
