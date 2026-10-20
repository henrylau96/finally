---
phase: 05-real-market-data-massive
reviewed: 2026-10-20T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - backend/app/api/health.py
  - backend/app/main.py
  - backend/app/market/__init__.py
  - backend/app/market/cache.py
  - backend/app/market/factory.py
  - backend/app/market/interface.py
  - backend/app/market/massive_parse.py
  - backend/app/market/massive_source.py
  - backend/app/market/simulator_source.py
  - backend/pyproject.toml
  - backend/tests/conftest.py
  - backend/tests/market/test_cache.py
  - backend/tests/market/test_factory.py
  - backend/tests/market/test_massive_parse.py
  - backend/tests/market/test_massive_source.py
  - backend/tests/test_health.py
  - frontend/src/components/Header.tsx
  - frontend/src/components/Terminal.tsx
  - frontend/src/lib/usePriceStream.ts
  - test/e2e/01-fresh-start.spec.ts
findings:
  critical: 1
  warning: 4
  info: 5
  total: 10
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-10-20
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

I reviewed the Phase 5 diff (`773b3f0^..HEAD`): the Massive REST source, the parsing helpers, the cache reference close, the factory, the health `source` field, and the EOD stale badge. The simulator path, health and E2E changes are fine. The problems are in `MassiveDataSource`. It only detects the snapshot-vs-EOD plan inside the bulk poll, and that poll is skipped when no tickers are tracked, so on a free-tier key trades can stay broken for good. It also ignores the free-tier call budget and the SDK's retry behaviour. And the lifespan blocks on network I/O before the app can serve.

## Critical Issues

### CR-01: Free tier with no tracked tickers never switches to EOD, so trades fail permanently

**File:** `backend/app/market/massive_source.py:79-110` (with `backend/app/services.py:62-70`)
**Issue:** The switch to `eod` mode only happens inside the `get_snapshot_all` branch of `_poll_once`. `_poll_once` returns early when `self._tickers` is empty (line 91-92). `_fetch_one` in snapshot mode calls `get_snapshot_ticker`, which raises `NOT_AUTHORIZED` on the free plan, and `add_ticker` logs and swallows that. Reproduction with a free-tier key, an empty watchlist and no positions:
1. `start([])` skips the poll, so `_mode` stays `"snapshot"`.
2. `place_trade("AAPL")` calls `add_ticker`. The 403 is logged and the cache stays empty, so the trade fails with `TradeError("No price available")`.
3. In the `finally`, `reconcile_stream` calls `remove_ticker`, so `_tickers` is empty again.
4. Every loop poll returns early, so the mode never flips, and every later trade (REST or AI chat) fails the same way, forever.

The same 403 in `add_ticker` also means that, in snapshot mode before the first switch, a newly watched ticker has no price until the next poll.
**Fix:** Handle the entitlement error where a single quote is fetched too, and switch modes there:
```python
async def _fetch_one(self, ticker: str) -> Quote | None:
    if self._mode == "snapshot":
        try:
            snap = await asyncio.to_thread(self._client.get_snapshot_ticker, "stocks", ticker)
            return snapshot_quote(snap)
        except Exception as e:
            if not not_authorized(e):
                raise
            self._enter_eod()  # sets _mode = "eod" and raises _interval to EOD_MIN_INTERVAL
    if ticker in self._bars:
        return bar_quote(self._bars[ticker])
    bars = await asyncio.to_thread(self._client.get_previous_close_agg, ticker, adjusted=True)
    return bar_quote(bars[0]) if bars else None
```
Have `_poll_once` use the same `_enter_eod()` helper. Add a test: `start([])` with a 403 single-snapshot client, then `add_ticker` should return a price.

## Warnings

### WR-01: Startup and EOD polls can go over the free-tier 5 calls/min budget, and SDK retries make it worse

**File:** `backend/app/market/massive_source.py:42-49, 112-117`; `backend/app/market/massive_parse.py:38-51`
**Issue:** On the free tier, `start()` makes 1 `get_snapshot_all` call (403) and then up to 5 `get_grouped_daily_aggs` calls. For example, on a Tuesday after a Monday holiday it requests Tue (403), Mon, Sun, Sat, then Fri: 6 requests in the same second. `add_ticker` calls `get_previous_close_agg` too, so several AI-chat watchlist adds right after startup add more calls. The Massive `RESTClient` defaults to `retries=3` with `status_forcelist` including 429 and a 0.1s backoff (`massive/rest/base.py:61-73`). Each 429 is retried at once, which uses up even more quota. After the retries run out, urllib3 raises `MaxRetryError`, not `BadResponse`, so the `except BadResponse` step-back in `latest_grouped_bars` never sees it. The whole poll fails, and the next try is 900 s later. The startup window, when the cache is empty and trades fail, can therefore last 15 minutes.
**Fix:** Cache the resolved trading day and only re-walk days after it changes, so later polls cost 1 call. Build the client with `RESTClient(api_key=key, retries=0)` so a 429 surfaces once as an error. If the first EOD poll fails, retry it on a short delay (for example 60 s) instead of waiting the full 900 s.

### WR-02: Lifespan blocks on Massive network I/O before the app serves

**File:** `backend/app/main.py:49`; `backend/app/market/massive_source.py:42-49`
**Issue:** `source.start()` awaits `_poll_once()` inline in the lifespan. With the SDK defaults (10 s connect plus 10 s read, 3 retries) and up to 6 sequential calls, a slow or unreachable API can hold startup for minutes. During that time `/api/health` does not answer, the container healthcheck can fail, and the user sees no UI at all, not just stale prices.
**Fix:** Start the loop task first and let it do the first poll, so `start()` returns right away:
```python
async def start(self, tickers: list[str]) -> None:
    self._tickers = list(tickers)
    self._task = asyncio.create_task(self._run_loop(), name="massive-loop")

async def _run_loop(self) -> None:
    while True:
        try:
            await self._poll_once()
        except Exception:
            logger.exception("Massive poll failed")
        await asyncio.sleep(self._interval)
```
Or, at minimum, pass shorter `connect_timeout`/`read_timeout` to `RESTClient`.

### WR-03: An invalid API key produces a traceback every poll with no visible signal

**File:** `backend/app/market/massive_source.py:98-100, 123-129`
**Issue:** A wrong or revoked key returns a non-`NOT_AUTHORIZED` error (401 "Unknown API Key"). This error is re-raised and logged with `logger.exception` every 15 s, forever. The cache stays empty, but `/api/health` still reports `{"status": "ok", "source": "massive"}`. Every trade fails with "No price available" and the user gets no hint why. The poll loop and `add_ticker` flood the logs with full tracebacks for one predictable condition.
**Fix:** Log `BadResponse` as one-line `logger.error("Massive poll failed: %s", e)` and keep `logger.exception` for unexpected errors. Optionally expose a `last_error` on the source so health or the header can show it.

### WR-04: The cache version bumps on every poll, so the frontend appends duplicate sparkline points

**File:** `backend/app/market/massive_source.py:105-117`; `frontend/src/lib/usePriceStream.ts:64-68`
**Issue:** Every poll rewrites every ticker, even when nothing changed (EOD bars are the same all day, and snapshots outside market hours do not move). Each write increments `PriceCache.version`, so SSE pushes a full payload. `history` then appends the same price for every ticker on every push. In EOD mode an add or remove of any ticker triggers a push too. The sparklines fill with flat duplicate points that look like live ticks. The `chart` path avoids this by de-duplicating on timestamp, but `history` does not.
**Fix:** Skip `_write` when the cached price and timestamp are already the same:
```python
def _write(self, ticker: str, quote: Quote) -> None:
    price, ts, ref = quote
    cur = self._cache.get(ticker)
    if cur and cur.timestamp == ts and cur.price == round(price, 2):
        return
    self._cache.update(ticker, price, timestamp=ts, reference=ref)
```

## Info

### IN-01: EOD day change is open-to-close, while snapshot mode uses previous close

**File:** `backend/app/market/massive_parse.py:33-35`
**Issue:** `bar_quote` uses `bar.open` as the reference, so in EOD mode "daily change %" means intraday open to close. In snapshot mode it means previous close to last. The same column changes meaning depending on the plan.
**Fix:** Document it in the UI tooltip, or compute the reference from the previous trading day's grouped bar (which costs one extra call).

### IN-02: `latest_grouped_bars` returns an empty dict when a day has bars but none have a close

**File:** `backend/app/market/massive_parse.py:48-49`
**Issue:** The `if bars:` check runs before the `b.close` filter. A day whose bars all have `close == 0` returns `{}` instead of stepping back a day.
**Fix:** Filter first, then test: `found = {b.ticker: b for b in bars if b.close}; if found: return found`.

### IN-03: `MASSIVE_POLL_INTERVAL` of 0 or a negative value makes a tight poll loop

**File:** `backend/app/market/factory.py:18`
**Issue:** `float("0")` gives `asyncio.sleep(0)` in snapshot mode, which hammers the API and hits the rate limit within seconds. EOD mode is protected by `max(..., EOD_MIN_INTERVAL)`, but snapshot mode is not.
**Fix:** `interval = max(1.0, float(...))`, or document the minimum in `.env.example`.

### IN-04: The "EOD" badge also shows on a paid snapshot plan outside market hours

**File:** `frontend/src/lib/usePriceStream.ts:61-62`; `frontend/src/components/Header.tsx:35-39`
**Issue:** Staleness is based only on how old the timestamp is (more than 300 s). On a snapshot-tier key after hours or at weekends, `last_trade` is hours old, so the header says "EOD · as of ...". The source is not end-of-day bars there. The text is misleading, though the date shown is correct.
**Fix:** Use a neutral label such as "Delayed · as of ...", or include the source mode in the SSE payload or health response.

### IN-05: The poll-loop test depends on timing

**File:** `backend/tests/market/test_massive_source.py:169-179`
**Issue:** The test uses `interval=0.02` and two `sleep(0.06)` windows with `asyncio.to_thread` calls in between. On a loaded WSL or CI host the second window can contain zero polls, so the test can fail intermittently.
**Fix:** Poll until a call-count condition is met within a generous deadline (for example up to 1 s), instead of using fixed sleeps.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
