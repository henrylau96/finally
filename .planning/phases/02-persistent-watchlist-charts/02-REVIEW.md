---
phase: 02-persistent-watchlist-charts
reviewed: 2026-10-19T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - .gitignore
  - backend/app/api/watchlist.py
  - backend/app/db.py
  - backend/app/main.py
  - backend/db/schema.sql
  - backend/tests/conftest.py
  - backend/tests/test_db.py
  - backend/tests/test_watchlist_api.py
  - frontend/package.json
  - frontend/src/app/globals.css
  - frontend/src/components/MainChart.tsx
  - frontend/src/components/Panel.tsx
  - frontend/src/components/Terminal.tsx
  - frontend/src/components/Watchlist.tsx
  - frontend/src/components/WatchlistAddForm.tsx
  - frontend/src/components/WatchlistRow.tsx
  - frontend/src/lib/usePriceStream.ts
  - frontend/src/lib/useWatchlist.ts
findings:
  critical: 1
  warning: 2
  info: 6
  total: 9
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-19
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

I reviewed the Phase 2 diff (2fa9de2..HEAD): the SQLite layer, the watchlist REST API, lifespan wiring, the watchlist add/remove UI and the Lightweight Charts main chart. The backend suite passes (44 tests). The DB layer is sound: queries are parameterized, every DB call runs through `asyncio.to_thread`, seeding is idempotent and the unique constraints work.

There is one confirmed input-validation bug. The ticker validator turns JSON `null`/`true`/`false` into the strings `"NONE"`/`"TRUE"`/`"FALSE"` and accepts them. This was reproduced against the running app. The frontend has two robustness issues. First, the chart's "already shown" ref is not reset when the chart instance is recreated. Second, concurrent watchlist reloads can apply stale results.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Ticker validator accepts JSON null and booleans as tickers "NONE"/"TRUE"/"FALSE"

**File:** `backend/app/api/watchlist.py:17-24`
**Issue:** The `mode="before"` validator runs `str(v)` before any type check. So `{"ticker": null}` becomes `"NONE"` and `{"ticker": true}` becomes `"TRUE"`. Both match `[A-Z]{1,5}` and are added to the watchlist with 201. They persist in SQLite and the simulator streams them. Reproduced:
```
{'ticker': None} 201 NONE
{'ticker': True} 201 TRUE
```
The API contract says invalid input returns 422. When Phase 4 lands, a malformed LLM `watchlist_changes` entry (`"ticker": null`) would also go through this path and add junk tickers.
**Fix:** Let pydantic enforce `str` first, then normalize in an after-validator:
```python
class AddTicker(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def normalize(cls, v: str) -> str:
        """Trim, uppercase and require 1-5 letters."""
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{1,5}", v):
            raise ValueError("ticker must be 1-5 letters")
        return v
```
Add `None` and `True` to the `test_invalid` parametrize list.

## Warnings

### WR-01: MainChart does not repaint history after the chart instance is recreated

**File:** `frontend/src/components/MainChart.tsx:68-93`
**Issue:** The `shown` ref (the last ticker sent to `setData`) outlives the chart. The cleanup in the first effect removes the chart and builds a new one, but leaves `shown.current` set. React StrictMode in `next dev` mounts, unmounts and remounts every effect, and the App Router enables StrictMode by default. Fast Refresh does the same. On remount, the second effect sees `shown.current === ticker` and only calls `series.update(last)`, so the new series has one point and the earlier history is lost. The chart stays wrong until the user selects another ticker. Production builds do not double-mount, so the bug only appears in dev. It still makes the chart look broken during development and E2E runs against `next dev`.
**Fix:** Reset the sync refs when the chart is torn down, so the next effect pass calls `setData`:
```tsx
return () => {
  chart.remove();
  chartRef.current = null;
  seriesRef.current = null;
  shown.current = "";
  lastTime.current = 0;
};
```
`shown` must differ from any real ticker after this. If `ticker` can be `""`, use a sentinel such as `null`.

### WR-02: Concurrent watchlist reloads can apply a stale list

**File:** `frontend/src/lib/useWatchlist.ts:19-32, 49, 63`
**Issue:** Each successful add or remove calls `load()`, and nothing orders the responses. Each row has its own `pending` flag, so two removes can be in flight at once (for example, × on NFLX and then × on V right away). The second GET can then resolve before the first. When the first GET's response arrives last, `setRows` writes a list that still contains the ticker removed by the later action. The UI then shows a row that is gone from the DB and the stream, with a `--` price, until the next add or remove.
**Fix:** Apply only the latest load:
```ts
const seq = useRef(0);
const load = useCallback(async () => {
  const id = ++seq.current;
  try {
    const res = await fetch("/api/watchlist");
    const data = res.ok ? await res.json() : null;
    if (id !== seq.current) return;
    if (data) { setRows(data); setError(false); } else setError(true);
  } catch {
    if (id === seq.current) setError(true);
  }
  if (id === seq.current) setLoading(false);
}, []);
```

## Info

### IN-01: The DB write and the market source update are not atomic across awaits

**File:** `backend/app/api/watchlist.py:48-62`
**Issue:** POST commits the DB insert in a worker thread, then calls `await source.add_ticker`. DELETE does the reverse. Suppose a DELETE for the same ticker runs between POST's insert and POST's `source.add_ticker`. The ticker ends up streamed but not on the watchlist (it disappears on restart). I could not reproduce this (0 of 300 concurrent add/delete pairs diverged). The window is still real, and Phase 4 chat actions make concurrent mutations more likely.
**Fix:** Serialize watchlist mutations with one `asyncio.Lock` held around the DB call and the source call in both handlers.

### IN-02: The first page load shows "Prices may be stale" before any connection exists

**File:** `frontend/src/components/Watchlist.tsx:16-21`
**Issue:** `usePriceStream` starts in `status = "reconnecting"`, so a fresh load shows "Reconnecting to price stream. Prices may be stale." when nothing has connected yet. As a result, "Loading watchlist..." is effectively never shown. This matches UI-SPEC row 2 ("including initial Connecting"), but the copy is misleading, and `hasConnected` is already available in Terminal.
**Fix (optional):** Pass `hasConnected` and show a "Connecting to price stream..." message until the first `onopen`.

### IN-03: A watchlist load failure shows "Add a ticker to see its chart."

**File:** `frontend/src/components/Terminal.tsx:20-24`, `frontend/src/components/MainChart.tsx:110-114`
**Issue:** When `GET /api/watchlist` fails, `rows` is `[]` and `loading` is false. The effect then sets `selected` to `""`, and the chart tells the user to add a ticker even though the real problem is a load error. Before the first load, the default `"AAPL"` is also briefly shown even if AAPL was removed and that removal persisted.
**Fix:** Skip the reselect effect while `error` is true. Optionally start `selected` at `""` until the first load resolves.

### IN-04: The chart's incremental update assumes one new point per render

**File:** `frontend/src/components/MainChart.tsx:89-92`
**Issue:** Only `points[points.length - 1]` is pushed. If React batches two SSE messages into one commit (for example, when a background tab delivers buffered events back to back), any whole-second point in between is missing from the series until the ticker is reselected. The impact is low because ticks within the same second are merged anyway.
**Fix:** Push every point newer than `lastTime.current`: `for (const p of points) if (p.time >= lastTime.current) series.update(p)`.

### IN-05: Misleading test helper `reenter`

**File:** `backend/tests/test_watchlist_api.py:63-68`
**Issue:** The docstring says it opens "a fresh lifespan and client", but it only builds a client. The `db_env` parameter is unused, and the function is `async` for no reason.
**Fix:** Make it a plain `def client_for_app()` with an accurate docstring, or move it into conftest.

### IN-06: Grid template duplicated between header and row

**File:** `frontend/src/components/Watchlist.tsx:7`, `frontend/src/components/WatchlistRow.tsx:51`
**Issue:** `grid-cols-[72px_1fr_72px_72px_24px]` is defined twice. If one copy changes without the other, the header and the rows misalign.
**Fix:** Export `GRID` from one module and use it in both.

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
