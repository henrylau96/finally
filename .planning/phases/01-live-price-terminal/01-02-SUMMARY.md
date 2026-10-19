---
phase: 01-live-price-terminal
plan: 02
subsystem: ui
tags: [nextjs, react, tailwind, eventsource, static-export]

requires:
  - phase: 01-live-price-terminal
    provides: SSE /api/stream/prices, /api/health, STATIC_DIR mount (plan 01)
provides:
  - frontend Next.js 16.4.2 static export project with Tailwind theme tokens, lint, typecheck
  - usePriceStream hook (status, quotes, 120-point history)
  - Minimal live Terminal component with E2E test ids
affects: [01-03, 01-04, 01-05]

tech-stack:
  added: [next 16.4.2, react 19.3.1, tailwindcss 4, typescript ~5.9, eslint 10, eslint-config-next]
  patterns:
    - "Phase-aware next.config.ts: export for build, /api rewrites only in dev"
    - "setState only inside EventSource handlers"

key-files:
  created:
    - frontend/package.json
    - frontend/next.config.ts
    - frontend/src/app/globals.css
    - frontend/src/lib/usePriceStream.ts
    - frontend/src/lib/tickers.ts
    - frontend/src/components/Terminal.tsx
  modified:
    - .gitignore

key-decisions:
  - "Exact-pinned next/react/react-dom (npm defaulted to caret ranges)"
  - "Ignore frontend/next-env.d.ts and tsconfig.tsbuildinfo as generated"

requirements-completed: [UI-01, OPS-01, STRM-01, STRM-04]

duration: 20min
completed: 2026-10-19
---

# Phase 1 Plan 02: Frontend Live Ticker Skeleton Summary

**Next.js static export with dark Tailwind theme and an EventSource hook, showing 10 live ticker rows and a connection-status dot, served by FastAPI from one origin.**

## Accomplishments
- Scaffold builds to `frontend/out`; lint, typecheck, build all clean; theme tokens compiled into emitted CSS.
- Smoke on port 8010 with `STATIC_DIR=../frontend/out`: `/` returns 200 text/html containing `watchlist-row-AAPL`, `/api/health` returns `{"status":"ok"}`, stream yields `data:` frames. Static HTML has 10 distinct row ids and `connection-status` with `data-status="reconnecting"`.
- Browser rendering was not eyeballed (no browser run); verification is build, grep and curl.

## Task Commits
1. Task 1 (scaffold): c6351d8
2. Task 2 (hook + Terminal): a3957bc

## Deviations from Plan

**1. [Rule 3 - Blocking] Extra gitignore entry**
- `tsc` with `incremental` emits `frontend/tsconfig.tsbuildinfo`; added to `.gitignore` (in c6351d8).

**2. Exact version pins**
- npm saved `^` ranges; edited package.json to exact `next`, `react`, `react-dom` per acceptance criteria and re-ran `npm install`.

## Known Stubs
Rows show `--` until the first quote and have no Day %/sparkline/flash; intentional, plan 01-04 replaces the minimal markup.

## Issues Encountered
First smoke run hit the server before it finished starting (slow /mnt/c); the slow instance was stopped and a rerun passed. No servers left running.

## Self-Check: PASSED
