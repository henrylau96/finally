---
phase: 04-ai-chat-copilot
plan: 02
subsystem: frontend
tags: [ui, e2e, a11y]
requires: []
provides: [enter-to-buy, persistent-selection, heatmap-button-cells]
affects: [frontend/src/components/TradeBar.tsx, Terminal.tsx, Heatmap.tsx]
key-files:
  modified:
    - frontend/src/components/TradeBar.tsx
    - frontend/src/components/Terminal.tsx
    - frontend/src/components/Heatmap.tsx
    - test/e2e/03-trading.spec.ts
    - test/e2e/04-portfolio-viz.spec.ts
decisions:
  - "Selection default assigned only when empty; sold-out or removed tickers stay selected"
metrics:
  tasks: 2
  completed: 2026-10-19
requirements: [UI-11]
---

# Phase 4 Plan 02: Phase 3 UI-audit fold-ins Summary

Enter in the trade bar buys, the selected ticker survives sell-out, and heatmap cells are accessible buttons with a visible selection ring.

## Tasks

1. RED (dc06e6c): new E2E for Enter-buy (both inputs), selection after selling out an unwatched ZZZZ, heatmap role/aria-pressed. All three failed on the old build; the selection test failed at the final data-ticker assertion (received "AAPL"), so it genuinely exercised the bug. Existing tests still passed.
2. GREEN: TradeBar `buyOnEnter` on both inputs (Buy/Sell stay type="button"); Terminal effect only defaults when nothing is selected; Heatmap cells role="button", aria-pressed, 2px primary inset ring on data-selected.

Verification: lint, typecheck, build clean; Playwright 01 then 02, 03, 04 all pass on a fresh mock server (port 8024, scratch DB).

## Deviations from Plan

None - plan executed as written.

## Self-Check: PASSED
