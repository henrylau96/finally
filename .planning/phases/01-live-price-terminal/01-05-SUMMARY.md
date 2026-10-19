---
phase: 01-live-price-terminal
plan: 05
subsystem: ops
tags: [readme, smoke-test, uvicorn, sse, playwright]

requires:
  - phase: 01-live-price-terminal
    provides: backend static serving and SSE (plan 03), terminal UI (plan 04)
provides:
  - Documented single-origin local run command with graceful shutdown timeout
  - Verified integrated tree (backend suite, frontend lint/typecheck/build, restart smoke)
  - Human approval of the live terminal in a browser
affects: [phase-2]

tech-stack:
  added: []
  patterns:
    - "Local full-stack run: STATIC_DIR=../frontend/out uv run uvicorn app.main:app --timeout-graceful-shutdown 2"

key-files:
  created: []
  modified:
    - README.md

key-decisions:
  - "--timeout-graceful-shutdown 2 documented so open SSE connections do not block server exit"

patterns-established:
  - "Use explicit PIDs to stop servers; pkill -f with the uvicorn pattern kills the invoking shell"

requirements-completed: [OPS-01, OPS-02, STRM-01, STRM-02, STRM-04, UI-03, UI-04, TEST-01]

duration: n/a
completed: 2026-10-19
---

# Phase 1 Plan 05: Local Run, Integration Smoke and Human Verification Summary

**README documents the one-origin local run command; the integrated tree passes all suites, survives a server restart with SSE resuming, and a human approved the live terminal.**

## Accomplishments

- Added a concise Development section to README.md with the full-stack run command including `--timeout-graceful-shutdown 2`.
- Verified integrated tree:
  - Backend pytest: 27 passed
  - Frontend lint, typecheck, build: passed
  - Server smoke on port 8010: health `{"status":"ok"}`, `/` 200 text/html, 8 SSE data frames in 4 s, first frame has 10 tickers with 6 keys each, `/api/nope` 404, process exits within 3 s after SIGINT, restart streamed 4 frames in 2 s
  - Playwright against 8010: `06-sse-reconnect.spec.ts` (1 passed), `01-fresh-start.spec.ts -g "health|prices stream"` (2 passed)
- Dockerfile untouched.
- Human checkpoint: user viewed http://localhost:8010, stopped server with `kill -INT`, and responded "approved".

## Task Commits

1. Task 1: Document local run and pass full suite plus restart smoke - `1dbf442`
2. Task 2: Human verification of live terminal - approved (no commit)

## Deviations from Plan

None - plan executed as written. Note: `pkill -f` with the uvicorn pattern killed the executor's own shell; explicit PIDs were used afterward.

## Known Stubs

None.

## Self-Check: PASSED

Commit 1dbf442 present in git log; README.md modified.
