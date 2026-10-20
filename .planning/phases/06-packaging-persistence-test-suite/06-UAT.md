---
status: diagnosed
phase: 06-packaging-persistence-test-suite
source: [06-05-SUMMARY.md]
started: 2026-10-20T06:10:00Z
updated: 2026-10-20T06:25:00Z
---

## Current Test

[testing paused - gap closure chosen: load Massive daily history for the main chart]

## Tests

### 1. Main chart shows price history for the selected ticker
expected: Clicking a watchlist ticker shows a price-over-time chart in the main chart area
result: issue
reported: "the individual chart for the tickers is not showing"
severity: major

### 2. Remaining 06-05 human checks (layout widths, persistence across restart)
expected: As listed in 06-05-PLAN.md Task 3
result: [pending]

## Summary

total: 2
passed: 0
issues: 1
pending: 1
skipped: 0
blocked: 0

## Gaps

- truth: "The main chart shows a price-over-time line for the selected ticker, also when the market data source is Massive end-of-day (free tier)"
  status: failed
  reason: "User reported: the individual chart for the tickers is not showing"
  severity: major
  test: 1
  root_cause: "With MASSIVE_API_KEY set on the free tier, the source serves end-of-day data: every SSE quote carries the same timestamp (1792440000 = 2026-10-19T20:00Z) and a flat price. usePriceStream.appendPoint replaces a point with an equal time, so each ticker keeps exactly 1 ChartPoint. MainChart renders the 'Collecting price data...' overlay while points.length < 2, so it never clears. Proven: SSE capture of /api/stream/prices and browser check at 1920 width (chart 846x590, canvases drawn, overlay text present after 8s). Sparklines stay empty for the same reason. Not a Phase 6 layout regression; E2E passes because it runs on the simulator."
  artifacts:
    - frontend/src/components/MainChart.tsx
    - frontend/src/lib/usePriceStream.ts
    - backend market data Massive source (massive client / source module)
  missing:
    - "Backend endpoint returning recent daily bars for one ticker from Massive (e.g. GET /api/history/{ticker}); simulator source can return its accumulated or empty history"
    - "MainChart seeds the series from that history on ticker select, then appends live SSE points"
    - "Tests: backend route/parse test for daily bars, frontend test for seeded chart; free-tier rate limit (5 calls/min) respected (cache bars per ticker)"
  debug_session: ""
