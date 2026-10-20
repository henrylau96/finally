---
phase: 06-packaging-persistence-test-suite
reviewed: 2026-10-20T15:45:00Z
depth: standard
files_reviewed: 38
files_reviewed_list:
  - backend/app/api/history.py
  - backend/app/main.py
  - backend/app/market/interface.py
  - backend/app/market/massive_parse.py
  - backend/app/market/massive_source.py
  - backend/app/market/simulator_source.py
  - backend/tests/market/test_interface.py
  - backend/tests/market/test_massive_parse.py
  - backend/tests/market/test_massive_source.py
  - backend/tests/test_routes_smoke.py
  - frontend/src/components/ChatDock.test.tsx
  - frontend/src/components/ChatDock.tsx
  - frontend/src/components/Header.test.tsx
  - frontend/src/components/Header.tsx
  - frontend/src/components/MainChart.test.tsx
  - frontend/src/components/MainChart.tsx
  - frontend/src/components/PositionsTable.test.tsx
  - frontend/src/components/PositionsTable.tsx
  - frontend/src/components/PriceCell.test.tsx
  - frontend/src/components/Sparkline.tsx
  - frontend/src/components/Terminal.tsx
  - frontend/src/components/TradeBar.tsx
  - frontend/src/components/Watchlist.test.tsx
  - frontend/src/components/Watchlist.tsx
  - frontend/src/components/WatchlistRow.tsx
  - frontend/src/lib/chartPoints.test.ts
  - frontend/src/lib/chartPoints.ts
  - frontend/src/lib/chartTheme.ts
  - frontend/src/lib/portfolio.test.ts
  - frontend/src/lib/useHistory.ts
  - frontend/src/lib/useHistorySeeds.test.ts
  - frontend/src/lib/useHistorySeeds.ts
  - frontend/vitest.config.mts
  - frontend/vitest.setup.ts
  - test/e2e/01-fresh-start.spec.ts
  - test/e2e/03-trading.spec.ts
  - test/e2e/07-responsive.spec.ts
  - test/persistence.sh
findings:
  critical: 1
  warning: 5
  info: 6
  total: 12
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-10-20T15:45:00Z
**Depth:** standard
**Files Reviewed:** 38
**Status:** issues_found

## Summary

This phase adds daily price history (`/api/history/{ticker}`, `MassiveDataSource.history`), seeds the main chart and sparklines from it, adds a tablet layout with an overlay chat dock, and adds test infrastructure: vitest, the responsive E2E spec and `test/persistence.sh`. The unit suites pass (backend 187, frontend 42). Passing tests do not show the feature is correct, though.

Key concerns:
- The EOD history throttle counts only history calls. It ignores the poll and add-ticker calls that share the same 5/min free-tier quota, so the history seeding breaks on the plan it was throttled for.
- The frontend stores failed history fetches as permanent empty seeds and never retries them.
- The tablet layout makes the watchlist column narrower than its own fixed grid tracks. The responsive E2E spec only measures document-level scroll, so it cannot see this.
- Chart time formatting was written for intraday ticks and is wrong for daily points (crosshair shows a clock time, and day labels shift by a day for users west of New York).

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: The EOD history throttle ignores poll and add-ticker calls, so the free-tier 5/min quota is exceeded on fresh start

**File:** `backend/app/market/massive_source.py:107-111`, `backend/app/market/massive_parse.py:12-13`
**Issue:** `HISTORY_SPACING = 15` is documented as "4/min under the free tier's 5/min". But `_last_history` only tracks `get_aggs` calls. In EOD mode the same key also makes these calls:
- `start()` -> `_safe_poll()`: `get_snapshot_all` (the 403 that switches to EOD) plus `latest_grouped_bars`. That is 2 calls on Tue-Fri (today 403, yesterday OK) and up to 5 on Monday or after holidays (today 403, Sun empty, Sat empty, Fri).
- Every 900 s `_poll_eod` repeats the 1-5 grouped calls.
- `add_ticker` -> `_fetch_one` -> `get_previous_close_agg` for tickers not in `_bars`.

On a fresh start, `scripts/start_*` opens the browser right away. `useHistorySeeds` then fires the first history call with no wait (because `_last_history = -inf`), followed by one every 15 s. That is 3-5 startup calls plus 4 history calls, or 7-9 calls in the first minute. The massive client (`rest/base.py:61-73`) also retries 429 three times with a 0.1 s backoff, and each retry spends more quota. Failed history calls return `[]` uncached, and the frontend then caches that `[]` for the whole session (WR-01). Result: on the free tier, the first page load after start loses seeds for several tickers, which is the exact scenario the throttle was written for.
**Fix:** Put every Massive call behind one shared limiter instead of a history-only gap:
```python
async def _call(self, fn, *args, **kwargs):
    """Run one Massive request, spaced by HISTORY_SPACING in EOD mode."""
    async with self._api_lock:
        wait = self._last_call + HISTORY_SPACING - time.monotonic()
        if self._mode == "eod" and wait > 0:
            await asyncio.sleep(wait)
        self._last_call = time.monotonic()
        return await asyncio.to_thread(fn, *args, **kwargs)
```
Route `get_aggs`, `get_previous_close_agg` and each `get_grouped_daily_aggs` attempt through it. `latest_grouped_bars` would need to take an async fetch callable, or the loop would move into the source.

## Warnings

### WR-01: `useHistorySeeds` caches failures as permanent empty seeds; the backend deliberately does not

**File:** `frontend/src/lib/useHistorySeeds.ts:19-21`
**Issue:** A non-OK response or a network error stores `[]` for the ticker. Because the effect skips any ticker already present (`!(t in seeds)`), that ticker is never requested again for the life of the page. The backend docstring says the opposite ("A failed fetch returns [] uncached", `massive_source.py:89`) so that the next request can retry. A transient 429 or 5xx (see CR-01) therefore leaves a sparkline unseeded until a full reload. `useHistory.ts:16-19` drops failures without storing them, so the two hooks behave inconsistently. The test "stores [] on a non-ok response and moves on" locks in this behaviour.
**Fix:** Store only successful responses, and track failed tickers separately so the sequential loop moves on without making the failure permanent. For example, keep a `failed` ref that is cleared when `key` changes, or retry after a delay:
```ts
fetch("/api/history/" + next)
  .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
  .then(store)
  .catch(() => { failed.current.add(next); setTick((n) => n + 1); });
```

### WR-02: At tablet widths the watchlist column is narrower than its fixed grid tracks; rows overflow and the remove button is clipped

**File:** `frontend/src/components/Terminal.tsx:45`, `frontend/src/components/Watchlist.tsx:7`, `frontend/src/components/WatchlistRow.tsx:51`
**Issue:** Below `lg`, the outer grid gives the watchlist `minmax(240px,30%)`. At 768 px, 30% of 752 is 225.6 px, so the column resolves to 240 px. At `lg`, `minmax(240px,26%)` at 1024 px gives about 262 px. Each watchlist row needs:
- fixed tracks `72+72+72+24 = 240` px
- 4 gaps of 8 px = 32 px
- `px-2` = 16 px and `border-l-2` = 2 px
- the price column's min-content (`1fr` = `minmax(auto,1fr)`, about 60-75 px for `$190.00` in mono `text-sm`)

That is about 350-365 px of content in a 238-260 px panel. The Panel body is `overflow-auto`, so the overflow is clipped into a horizontal scroll inside the panel. The Day %, Chart and remove columns sit off-screen. That defeats the `max-lg:opacity-100` change on the remove button, which was meant to make removal reachable on touch devices. `07-responsive.spec.ts:3-6` only checks `document.documentElement.scrollWidth`, so it passes while the panel overflows.
**Fix:** Size the tablet watchlist column to its content (for example `minmax(360px,30%)` with a narrower chart track), or shrink the row tracks below `lg`, e.g. `max-lg:grid-cols-[56px_1fr_56px_48px_24px]`. Add an E2E assertion that the watchlist body has no internal horizontal overflow:
```ts
const over = await page.getByTestId("watchlist").locator("> div").evaluate((el) => el.scrollWidth - el.clientWidth);
expect(over).toBeLessThanOrEqual(0);
```

### WR-03: The EOD/stale indicator disappears entirely below `lg`

**File:** `frontend/src/components/Header.tsx:35-39`
**Issue:** The badge text is now wrapped in `hidden lg:inline`, and the outer `stale-badge` span has no other content. On tablets the user gets no signal that prices are end-of-day or stale, which is exactly the information the badge exists to show. The outer element still renders, so `Header.test.tsx:17` (`toBeInTheDocument`) passes while nothing is visible.
**Fix:** Show a short form below `lg` instead of nothing, and assert visible text in the test:
```tsx
<span data-testid="stale-badge" className="text-xs text-text-muted">
  <span className="lg:hidden">EOD</span>
  <span className="hidden lg:inline">EOD · as of {nyDate(asOf)}</span>
</span>
```

### WR-04: Chart time formatting is wrong for the new daily history points

**File:** `frontend/src/lib/chartTheme.ts:15-16,32,35`
**Issue:** The main chart now shows up to 180 days of daily bars, but the formatters still assume intraday ticks.
1. `localization.timeFormatter` always returns `clock(t)`, so hovering a daily point shows a time such as `00:00:00` or `21:00:00` and never the date.
2. `day(t)` formats in the browser's local zone. Massive daily aggregates start at midnight New York time, so in Central, Mountain or Pacific time every daily label falls on the previous calendar day. `Header.tsx` correctly pins `America/New_York`, so the header and the chart disagree.
3. `TickMarkType.Year` (0) is routed to `day()`, so year boundaries show `01 Jan` with no year.
**Fix:** Format dates in the exchange zone, include the date in the crosshair, and handle Year:
```ts
const NY = { timeZone: "America/New_York" } as const;
export const day = (t: number) => new Date(t * 1000).toLocaleDateString("en-GB", { ...NY, day: "2-digit", month: "short" });
// tickMarkFormatter: Year -> year, Month/DayOfMonth -> day(t), else clock(t)
// timeFormatter: (t) => day(t) + " " + clock(t)
```

### WR-05: EOD live quotes and daily history likely use different bar timestamps, so the "same time replaces last close" merge never fires

**File:** `backend/app/market/massive_parse.py:36-38,62-69`, `frontend/src/lib/chartPoints.ts:13-19`
**Issue:** `mergePoints` and `sparklineValues` rely on the EOD live point (`bar_quote` -> grouped bar `timestamp`) having the same time as the last history point (`get_aggs` day bar `timestamp`). The test fixture `BAR_T = 1760731200000` for grouped bars is 2025-10-17T20:00Z (16:00 ET). Massive/Polygon `/aggs/.../day` bars are stamped at the start of the window (midnight ET). If so, the live point is about 16 h later than the history close for the same day. The history point is then not replaced, and the chart and sparkline get a duplicate close for the same session. The unit tests `replaces the last close with a same-time live point` and `replaces the last history point on equal time` assume equal times and do not exercise real timestamps.
**Fix:** Verify against a live free-tier response. If they differ, normalize both to the NY trading date, for example by flooring both to NY midnight in `bar_quote` and `daily_points`, or by having `daily_points` replace the last point whenever it falls on the same NY date as the live quote.

## Info

### IN-01: The main chart fetches history a second time alongside the seeds

**File:** `frontend/src/components/Terminal.tsx:27-29`
**Issue:** `useHistory(selected)` refetches `/api/history/{selected}` even though `useHistorySeeds` already fetches every watched ticker. In EOD mode both requests queue on the same server lock and spacing gap. The backend cache usually absorbs this, but it does not when the first call failed.
**Fix:** Use `seeds[selected]`, and call `useHistory` only for a selected ticker that is not on the watchlist (a held-only position).

### IN-02: ChatDock decides collapsed state only on mount, after first paint

**File:** `frontend/src/components/ChatDock.tsx:37-40`
**Issue:** The static export renders `collapsed=false`. On tablets the expanded 360 px overlay paints over the content before the effect collapses it. Resizing across the 1280 px breakpoint later never re-evaluates the state.
**Fix:** Subscribe to the media query's `change` event, or render collapsed by default and expand on wide screens.

### IN-03: `/api/history` accepts any 1-5 letter ticker and holds a global lock across the 15 s spacing sleep

**File:** `backend/app/api/history.py:13-19`, `backend/app/market/massive_source.py:95-101`
**Issue:** Any client can queue requests for arbitrary symbols. In EOD mode each one holds `_history_lock` for up to 15 s, which delays seeds for watched tickers and uses up the API quota. `_history` also grows without bound. This is a single-user local app, so the impact is low.
**Fix:** Optionally restrict history to tickers in `source.get_tickers()` or held positions.

### IN-04: The chained signal handler calls `previous` even when it is `SIG_DFL`/`SIG_IGN`/`None`

**File:** `backend/app/main.py:32-41`
**Issue:** `signal.getsignal` can return the integers `SIG_DFL`/`SIG_IGN` or `None`. Calling them raises `TypeError` inside the handler. Under uvicorn the previous handler is callable, but under other hosts or test transports SIGTERM is `SIG_DFL`. Each lifespan startup also wraps the handler again without restoring it. This code predates the phase.
**Fix:** `if callable(previous): previous(signum, frame)`.

### IN-05: `test/persistence.sh` can pass against a stale image, and its POST failures carry no message

**File:** `test/persistence.sh:8,22-23,32`
**Issue:** The script runs `$IMAGE` without building it, so it can prove persistence for old code. `post()` uses `curl -sf` under `set -e`, so a failing POST exits with curl's code and no `FAIL:` line. Also, `VOLUME` is overridable and is deleted by `cleanup`, so `VOLUME=finally-data` would wipe the user's real data.
**Fix:** Build first or document the requirement. Use `post() { curl -sf ... || { echo "FAIL: POST $1" >&2; exit 1; }; }`. Refuse to run when `VOLUME` is `finally-data`.

### IN-06: Wall-clock upper bounds in the history throttle tests may flake

**File:** `backend/tests/market/test_massive_source.py` (`test_history_cached_skips_throttle`, `test_history_snapshot_mode_not_throttled`)
**Issue:** The assertions `< 0.1` s and `< 0.5` s depend on scheduler latency, and this repo runs on WSL over `/mnt/c`.
**Fix:** Monkeypatch `asyncio.sleep` in `massive_source` to record requested waits and assert on those instead of elapsed time.

---

_Reviewed: 2026-10-20T15:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
