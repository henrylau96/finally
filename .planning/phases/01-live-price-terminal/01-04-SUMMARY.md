---
phase: 01-live-price-terminal
plan: 04
subsystem: ui
tags: [react, tailwind, svg, sse, terminal-grid]

requires:
  - phase: 01-live-price-terminal
    provides: usePriceStream hook and minimal Terminal (plan 02)
provides:
  - Full-viewport terminal grid shell with header, panels and collapsible chat dock
  - Live watchlist with flashing PriceCell, signed Day % and inline SVG sparklines
  - Connection status indicator with Connecting/Live/Reconnecting/Offline states
affects: [01-05, phase-2]

tech-stack:
  added: []
  patterns:
    - "Flash via data-flash attribute toggled with double requestAnimationFrame"
    - "Inline SVG sparkline from 120-point buffer"

key-files:
  created:
    - frontend/src/components/Panel.tsx
    - frontend/src/components/Header.tsx
    - frontend/src/components/ConnectionStatus.tsx
    - frontend/src/components/ChatDock.tsx
    - frontend/src/components/Watchlist.tsx
    - frontend/src/components/WatchlistRow.tsx
    - frontend/src/components/PriceCell.tsx
    - frontend/src/components/Sparkline.tsx
    - frontend/src/lib/format.ts
  modified:
    - frontend/src/components/Terminal.tsx
    - frontend/src/lib/usePriceStream.ts
    - frontend/src/app/globals.css

key-decisions:
  - "Day % and flash direction come from backend fields; client never recomputes from previous_price"
  - "Stale data (status != connected) shown in muted color with no flash"

requirements-completed: [UI-01, UI-03, UI-04, STRM-04]

duration: 15min
completed: 2026-10-19
---

# Phase 1 Plan 04: Terminal Grid and Live Watchlist Summary

**Dark terminal grid with honest connection indicator and a live watchlist showing flashing prices, backend Day % and progressive SVG sparklines.**

## Accomplishments
- Task 1: grid shell (48px header, watchlist column, main chart, heatmap/positions/P&L placeholders, collapsible chat dock); `usePriceStream` now returns `hasConnected`.
- Task 2: Watchlist/WatchlistRow/PriceCell/Sparkline, format helpers, flash and reduced-motion CSS, empty/stale/closed notices.
- Lint, typecheck and build pass. Exported HTML has all test ids, 10 rows and 10 price cells, "Waiting for prices"; emitted CSS has `data-flash` selectors. Browser behavior not eyeballed (build and grep verification only).

## Task Commits
1. Task 1: 96cf5e1
2. Task 2: 3bec91a

## Deviations from Plan
Minor: Task 1 kept an inline row list inside the Watchlist panel as specified; Watchlist also takes `selected`/`onSelect` props (plan said Terminal passes them). Panel accepts extra HTML attributes (for `data-ticker`, `role`). Otherwise as written.

## Known Stubs
Main chart, heatmap, positions, P&L, chat dock, and header total/cash (`--`) are intentional labeled placeholders for later phases.

## Self-Check: PASSED
