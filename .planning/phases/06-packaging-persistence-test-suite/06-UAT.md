---
status: resolved
phase: 06-packaging-persistence-test-suite
source: [06-05-SUMMARY.md, 06-08-SUMMARY.md]
started: 2026-10-20T06:10:00Z
updated: 2026-10-20T08:00:00Z
---

## Current Test

[testing complete - user approved all 06-08 checks]

## Tests

### 1. Main chart shows price history for the selected ticker
expected: Clicking a watchlist ticker shows a price-over-time chart in the main chart area
result: pass
note: "Fixed by 06-06/06-07. Verified in browser on Massive source: AAPL shows ~6 months of daily closes (124 points from /api/history/AAPL). Re-approved by user in 06-08."

### 2. Remaining 06-05 human checks (layout widths, persistence across restart)
expected: As listed in 06-05-PLAN.md Task 3
result: pass
note: "User approved in 06-08: wide, 1024 and 768 layouts, data persists across stop/start."

### 3. Watchlist sparklines show price action per ticker
expected: Each watchlist row shows a sparkline mini-chart beside the ticker
result: pass
note: "Fixed by 06-09/06-10 (seeded sparklines, throttled history). User approved in 06-08 on Massive EOD data."

### 4. AI chat panel is visible on launch
expected: An AI chat panel is ready to assist on first launch (PLAN.md section 2)
result: pass
note: "User first reported it missing, then confirmed: The AI chatbot is there. It starts collapsed to a 48px strip below 1280px width (by design, 06-01)."

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "The main chart shows a price-over-time line for the selected ticker, also when the market data source is Massive end-of-day (free tier)"
  status: resolved
  reason: "User reported: the individual chart for the tickers is not showing"
  severity: major
  test: 1
  root_cause: "Massive free tier serves end-of-day data: every SSE quote for a ticker has the same timestamp, so the stream yields 1 ChartPoint per ticker and MainChart never leaves the 'Collecting price data...' overlay."
  artifacts:
    - frontend/src/components/MainChart.tsx
    - backend/app/api/history.py
  missing: []
  debug_session: ""

- truth: "Every watchlist row shows a sparkline, also when the market data source is Massive end-of-day (free tier)"
  status: resolved
  reason: "User reported: still the individual stock charts not showing"
  severity: major
  test: 3
  root_cause: "Same root cause as the main-chart gap, but 06-06/06-07 only seeded MainChart. Sparklines were fed only from SSE ticks; on Massive EOD every tick for a ticker has the same timestamp, so each sparkline held 1 point. Resolved by 06-09 (throttled history) and 06-10 (seeded sparklines)."
  artifacts:
    - frontend/src/components/Sparkline.tsx
    - frontend/src/components/Watchlist.tsx
    - frontend/src/components/Terminal.tsx
    - backend/app/api/history.py
    - backend/app/market/massive_source.py
  missing: []
  debug_session: ""
