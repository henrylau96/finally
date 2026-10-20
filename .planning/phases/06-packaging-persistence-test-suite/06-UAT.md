---
status: diagnosed
phase: 06-packaging-persistence-test-suite
source: [06-05-SUMMARY.md, 06-08 Task 1 checkpoint]
started: 2026-10-20T06:10:00Z
updated: 2026-10-20T07:00:00Z
---

## Current Test

[testing paused - gap closure chosen: seed watchlist sparklines from daily history; make the chat dock visible at common laptop widths]

## Tests

### 1. Main chart shows price history for the selected ticker
expected: Clicking a watchlist ticker shows a price-over-time chart in the main chart area
result: pass
note: "Fixed by 06-06/06-07. Verified in browser on Massive source: AAPL shows ~6 months of daily closes (124 points from /api/history/AAPL)."

### 2. Remaining 06-05 human checks (layout widths, persistence across restart)
expected: As listed in 06-05-PLAN.md Task 3
result: [pending]

### 3. Watchlist sparklines show price action per ticker
expected: Each watchlist row shows a sparkline mini-chart beside the ticker
result: issue
reported: "still the individual stock charts not showing"
severity: major

### 4. AI chat panel is visible on launch
expected: An AI chat panel is ready to assist on first launch (PLAN.md section 2)
result: issue
reported: "The AI chatbot is missing as well"
severity: major

## Summary

total: 4
passed: 1
issues: 2
pending: 1
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
  status: failed
  reason: "User reported: still the individual stock charts not showing"
  severity: major
  test: 3
  root_cause: "Same root cause as the main-chart gap, but 06-06/06-07 only seeded MainChart. Sparklines are fed only from SSE ticks; on Massive EOD every tick for a ticker has the same timestamp, so each sparkline holds 1 point. Sparkline.tsx draws the polyline only when points.length >= 2. Proven in browser on the rebuilt container (source massive): all 10 rows report data-points=1 and render an empty svg."
  artifacts:
    - frontend/src/components/Sparkline.tsx
    - frontend/src/components/Watchlist.tsx
    - frontend/src/components/Terminal.tsx
    - backend/app/api/history.py
    - backend/app/market/massive_source.py
  missing:
    - "Sparklines seeded from daily history (e.g. last ~30 closes) then appended with live ticks"
    - "Respect Massive free tier (5 calls/min): history fetches for all watchlist tickers on page load must not exhaust the limit; failed fetches are not cached, so naive per-row /api/history calls leave about half the rows empty. Consider a backend-side batched/throttled warm-up or serving the cached history tail with /api/watchlist"
    - "Tests: frontend test for seeded sparkline; backend test for the chosen batching/throttling"
  debug_session: ""

- truth: "The AI chat panel is visibly available on launch at common laptop browser widths"
  status: failed
  reason: "User reported: The AI chatbot is missing as well"
  severity: major
  test: 4
  root_cause: "By design from 06-01 (tablet layout), ChatDock.tsx initializes collapsed when window.matchMedia('(min-width: 1280px)') does not match, rendering only a 48px strip with a small chevron button. Proven in browser: loaded below 1280px it is collapsed (data-collapsed=true); reloaded at 1404px it starts expanded (360px); the toggle works. Windows display scaling (125-150%) puts many laptop browsers below 1280 CSS px, so users see no chat. The collapsed strip has no label, so it reads as missing."
  artifacts:
    - frontend/src/components/ChatDock.tsx
    - frontend/src/components/Terminal.tsx
    - test/e2e/07-responsive.spec.ts
  missing:
    - "Chat dock visible by default at laptop widths (lower the auto-collapse breakpoint to the tablet range, e.g. below 1024px) and/or a clearly labelled collapsed strip (e.g. vertical 'AI CHAT' label)"
    - "Keep 06-01 tablet guarantees (no horizontal scroll at 1024x768 and 768x1024); update 07-responsive spec and ChatDock tests to match"
  debug_session: ""
