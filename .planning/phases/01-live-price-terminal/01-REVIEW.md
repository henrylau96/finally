---
phase: 01-live-price-terminal
reviewed: 2026-10-19T09:13:09Z
depth: standard
files_reviewed: 41
files_reviewed_list:
  - .gitignore
  - backend/app/__init__.py
  - backend/app/api/__init__.py
  - backend/app/api/health.py
  - backend/app/api/stream.py
  - backend/app/main.py
  - backend/app/market/__init__.py
  - backend/app/market/cache.py
  - backend/app/market/factory.py
  - backend/app/market/interface.py
  - backend/app/market/models.py
  - backend/app/market/seed_prices.py
  - backend/app/market/simulator.py
  - backend/app/market/simulator_source.py
  - backend/pyproject.toml
  - backend/tests/market/test_cache.py
  - backend/tests/market/test_interface.py
  - backend/tests/market/test_simulator.py
  - backend/tests/market/test_source.py
  - backend/tests/market/test_stream.py
  - backend/tests/test_health.py
  - frontend/eslint.config.mjs
  - frontend/next.config.ts
  - frontend/package.json
  - frontend/postcss.config.mjs
  - frontend/src/app/globals.css
  - frontend/src/app/layout.tsx
  - frontend/src/app/page.tsx
  - frontend/src/components/ChatDock.tsx
  - frontend/src/components/ConnectionStatus.tsx
  - frontend/src/components/Header.tsx
  - frontend/src/components/Panel.tsx
  - frontend/src/components/PriceCell.tsx
  - frontend/src/components/Sparkline.tsx
  - frontend/src/components/Terminal.tsx
  - frontend/src/components/Watchlist.tsx
  - frontend/src/components/WatchlistRow.tsx
  - frontend/src/lib/format.ts
  - frontend/src/lib/tickers.ts
  - frontend/src/lib/usePriceStream.ts
  - frontend/tsconfig.json
findings:
  critical: 0
  warning: 3
  info: 7
  total: 10
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-19T09:13:09Z
**Depth:** standard
**Files Reviewed:** 41
**Status:** issues_found

## Summary

Reviewed the backend market data package (cache, GBM simulator, simulator source, SSE stream, app wiring) and the frontend terminal shell (price stream hook, watchlist, price flash, sparkline, layout). The code is small and readable. Backend tests pass (27 passed), and the frontend typecheck and lint are clean.

Verification beyond reading:
- **Shutdown hang (proven):** I started uvicorn, opened one `curl -N` client on `/api/stream/prices`, and sent SIGTERM. The server logged "Waiting for connections to close" and was still alive 25 s later. The stream kept emitting events the whole time.
- **Correlation matrix:** checked by hand. It stays positive definite for any mix of default and dynamically added tickers, so `np.linalg.cholesky` cannot fail.
- **`.gitignore`:** the `!frontend/src/lib/` negation works. `git check-ignore` does not ignore `frontend/src/lib/format.ts`.

I found no blockers. The main concerns are: graceful shutdown never completes while a browser is connected; the stream and simulator run as two independent 500 ms loops, which can make the flash direction disagree with what the user sees; and the frontend uses its own hard-coded ticker list instead of what the stream sends.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Server never shuts down gracefully while any SSE client is connected

**File:** `backend/app/api/stream.py:12-21`, `backend/app/main.py:20-24`
**Issue:** `price_events` is an endless `while True` generator. On SIGTERM, uvicorn waits for open connections to close before it runs lifespan shutdown. An `EventSource` never closes its connection, so the process hangs. I reproduced this: after SIGTERM the server logged "Waiting for connections to close. (CTRL+C to force quit)" and was still running 25 s later, still streaming. In Docker, `docker stop` will always wait the full 10 s and then SIGKILL. `source.stop()` and any future shutdown work (for example a final portfolio snapshot) never run.
**Fix:** Bound the graceful-shutdown wait in the server command. The Dockerfile and docs should use it:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 2
```
Alternatively, end the generator when the server is exiting, for example by checking a module-level `asyncio.Event` that a signal handler sets before uvicorn starts draining connections.

### WR-02: Stream polling is not tied to simulator ticks; the flash direction can contradict the displayed move

**File:** `backend/app/api/stream.py:15-21`, `backend/app/market/simulator_source.py:53-60`, `frontend/src/components/PriceCell.tsx:20-35`
**Issue:** The simulator loop and each SSE generator are separate `sleep(0.5)` loops with nothing linking their timing. Their periods drift slightly apart (simulator: 0.5 s plus step time; stream: 0.5 s plus snapshot time), so their phases cross over time. When that happens, the stream samples after two simulator steps and one step is never delivered. `direction` and `previous_price` are relative to the cache's last step, not to the price the client last displayed. Example: the client shows 100.00; step 1 sets 101.00 and is skipped; step 2 sets 100.50 with `direction: "down"`. The client moves from 100.00 to 100.50 and flashes red on an uptick, and the sparkline loses a point. A 28 s capture showed no skipped steps, but nothing prevents them.
**Fix:** Either push on change instead of polling (the cache sets an `asyncio.Event` or `Condition` that `price_events` awaits), or compute the flash direction on the client from the last price it rendered:
```ts
// usePriceStream: derive direction against the previously received quote
setQuotes((prev) => Object.fromEntries(Object.entries(next).map(([t, q]) => {
  const last = prev[t]?.price;
  const direction = last === undefined || q.price === last ? "flat" : q.price > last ? "up" : "down";
  return [t, { ...q, direction }];
})));
```

### WR-03: Watchlist renders a hard-coded frontend ticker list and ignores the tickers the stream sends

**File:** `frontend/src/components/Watchlist.tsx:52-62`, `frontend/src/lib/tickers.ts:1-3`
**Issue:** The rows come from a copy of `DEFAULT_TICKERS` kept in the frontend, which duplicates `backend/app/market/seed_prices.py:3`. Any ticker the backend streams that is not in this list is never shown, even though `usePriceStream` stores its quote and history. A ticker the backend drops stays as a permanent "--" row. `SimulatorDataSource.add_ticker` and `remove_ticker` already exist, so this mismatch appears as soon as watchlist mutation is wired up. The two lists can also drift silently.
**Fix:** Build the rows from the data the server sends, for example `Object.keys(quotes)` (dict order matches the backend insertion order), or later from `GET /api/watchlist`. Delete `frontend/src/lib/tickers.ts`. Until the first event arrives, keep only the "Waiting for prices" notice.

## Info

### IN-01: `SimulatorDataSource` lifecycle has no guards against misuse

**File:** `backend/app/market/simulator_source.py:26-31, 40-48`
**Issue:** Calling `start()` twice overwrites `self._task` without cancelling the first loop. Both loops then keep running, the tick rate doubles, and `stop()` cancels only the second one. Calling `add_ticker` or `remove_ticker` before `start()` raises `AttributeError` on `None`.
**Fix:** In `start()`, call `await self.stop()` first, or assert `self._task is None`. Create the `GBMSimulator` in `__init__` (with no tickers) so `_sim` is never `None`.

### IN-02: Watchlist ARIA table semantics are invalid; rows only respond to Enter

**File:** `frontend/src/components/Watchlist.tsx:41-51`, `frontend/src/components/WatchlistRow.tsx:24-29`, `frontend/src/components/Panel.tsx:12-21`
**Issue:** `role="table"` is on the whole `<section>`, which also contains the `<h2>` and the `Notice` text. The `role="row"` elements have no `role="columnheader"` or `role="cell"` children. Rows are focusable and clickable, but Space does nothing and the selected state is not exposed (no `aria-selected`).
**Fix:** Put `role="table"` on the inner wrapper, add `role="columnheader"` and `role="cell"` to the spans, handle `e.key === " "`, and set `aria-selected={selected}`.

### IN-03: `selected` state is not used by the main chart (`data-ticker=""` is hard-coded)

**File:** `frontend/src/components/Terminal.tsx:16, 23`
**Issue:** `selected` defaults to `"AAPL"` and the row highlight follows it, but the main chart panel always has `data-ticker=""` and the "Select a ticker" placeholder. Any E2E check that reads `data-ticker` after a click will fail.
**Fix:** `data-ticker={selected}`.

### IN-04: `day_change_pct` divides by `session_open` with no zero case

**File:** `backend/app/market/models.py:26-27`
**Issue:** `PriceCache.update` rounds prices to 2 dp. Any real-data price below $0.005 (the planned Massive source) becomes `0.0` session open, and `day_change_pct` then raises `ZeroDivisionError` inside `to_dict()`. That kills the SSE snapshot for every client.
**Fix:** Return `0.0` when `session_open == 0`, or do not round the stored open price.

### IN-05: Import-time filesystem side effect in `main.py`

**File:** `backend/app/main.py:14, 30`
**Issue:** Importing `app.main` (including from `tests/test_health.py`) creates `backend/static/`, or whatever `STATIC_DIR` points to. Because the mount already uses `check_dir=False`, the `mkdir` exists only to avoid per-request errors before the frontend is built. That is a test and dev concern leaking into the module import.
**Fix:** Move the `mkdir` into `lifespan`, or create the directory in the Dockerfile and dev script.

### IN-06: `PriceCache.version` is read without the lock the class says it uses

**File:** `backend/app/market/cache.py:1, 49-51`
**Issue:** The module docstring says the cache is "Thread-safe", but `version` reads `_version` without `_lock`, and `get_all()` and `version` are read separately in `stream.py:16-18`. The behaviour is fine under the GIL with one event loop, but the guarantee in the docstring is overstated.
**Fix:** Return `(version, snapshot)` together from one locked method, or drop the "thread-safe" claim.

### IN-07: Test gaps for the HTTP stream route, static mount, and the whole frontend

**File:** `backend/tests/market/test_stream.py`, `frontend/package.json:5-10`
**Issue:** The stream tests exercise only the `price_events` generator, not `GET /api/stream/prices` (content type, `retry:` line, JSON framing). Nothing tests the static mount. The frontend has no unit tests or test script at all, although PLAN.md section 12 requires component tests (price flash, rendering).
**Fix:** Add an httpx streaming test that reads the first `data:` frame from the route. Add Vitest and React Testing Library with tests for `formatPct`, `PriceCell` flash, and `usePriceStream` message handling.

---

_Reviewed: 2026-10-19T09:13:09Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
