---
phase: 01-live-price-terminal
fixed_at: 2026-10-19T09:30:00Z
review_path: .planning/phases/01-live-price-terminal/01-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 2
skipped: 1
status: partial
---

# Phase 1: Code Review Fix Report

**Fixed at:** 2026-10-19T09:30:00Z
**Source review:** .planning/phases/01-live-price-terminal/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 2
- Skipped: 1 (deferred to Phase 2)

## Fixed Issues

### WR-01: Server never shuts down gracefully while any SSE client is connected

**Files modified:** `backend/app/api/stream.py`, `backend/app/main.py`, `backend/tests/market/test_stream.py`
**Commit:** 0ff0f9b
**Applied fix:** `price_events` now loops `while not shutdown.is_set()`, where `shutdown` is a module-level `asyncio.Event` in `stream.py`. During lifespan startup, `main.py` wraps uvicorn's SIGINT/SIGTERM handlers so they set `shutdown` and then call uvicorn's own handler. Setting the event from lifespan shutdown would not have worked. uvicorn 0.54 `Server.shutdown` waits for open connections to close before it sends lifespan shutdown, so the stream has to end when the signal arrives. Added `test_stream_ends_on_shutdown`.
**Evidence:** Before the fix, with uvicorn on port 8013, one `curl -N` client, and SIGTERM, the server logged "Waiting for connections to close" and was still alive after 5 s. After the fix, the server exits within 1 s, logs "Application shutdown complete", and `source.stop()` runs. Backend tests: 28 passed. The `--timeout-graceful-shutdown 2` flag stays documented as a backstop. The Dockerfile was not changed (Phase 6).

### WR-02: Stream polling is not tied to simulator ticks; the flash direction can contradict the displayed move

**Files modified:** `frontend/src/lib/usePriceStream.ts`
**Commit:** 594f0a7
**Applied fix:** Added `withRenderedDirection(prev, next)`. It sets each quote's `direction` by comparing the new price to the last price the client rendered for that ticker: `flat` on the first quote or when the price is unchanged, otherwise `up` or `down`. `setQuotes` now uses it. `npm run typecheck` and `npm run lint` are clean.
**Status:** fixed: requires human verification (logic change). The fix makes the flash colour always match the move the user sees. It does not stop a skipped simulator step from being missed in the sparkline. That would need push-on-change streaming, which was kept out of scope to keep this fix simple.

## Skipped Issues

### WR-03: Watchlist renders a hard-coded frontend ticker list and ignores the tickers the stream sends

**File:** `frontend/src/components/Watchlist.tsx:52-62`
**Reason:** Deferred to Phase 2 by the orchestrator. The persistent watchlist from SQLite (WATCH-01..04) will replace the hard-coded `frontend/src/lib/tickers.ts` list with `GET /api/watchlist`.
**Original issue:** The rows come from a frontend copy of `DEFAULT_TICKERS`. Streamed tickers outside that list are never shown, and the two lists can drift apart.

---

_Fixed: 2026-10-19T09:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
