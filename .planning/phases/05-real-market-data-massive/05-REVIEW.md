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
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 5: Code Review Report (re-review after 05-04)

**Reviewed:** 2026-10-20
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

This is a re-review of the Phase 5 diff (`773b3f0^..HEAD`) after gap-closure plan 05-04.

**CR-01 is resolved.** `_fetch_one` (`massive_source.py:79-95`) now catches a `NOT_AUTHORIZED` error from `get_snapshot_ticker` and calls the shared `_enter_eod()` helper (lines 97-101). That helper sets `_mode = "eod"` and raises `_interval` to at least 900 s, and the code then falls through to `get_previous_close_agg`. `_poll_once` uses the same helper (line 115). Walking through the original reproduction (free-tier key, `start([])`, then `place_trade("AAPL")`): the first `add_ticker` now switches to EOD mode and prices the ticker from the previous close, so the trade succeeds. The mode stays `eod` after `reconcile_stream` removes the ticker, so later trades work too. The new test `test_add_ticker_empty_start_falls_back_to_eod` covers this path. All 57 market and health tests pass.

There are no Critical findings left. One new Warning (WR-05) affects the same `add_ticker` path: I reproduced a case where a ticker is tracked but has no price. All earlier Warnings and Info items are still present and unchanged. Their line references below are updated to the current code.

## Warnings

### WR-01: Startup and EOD polls can go over the free-tier 5 calls/min budget, and SDK retries make it worse (still present)

**File:** `backend/app/market/factory.py:19`; `backend/app/market/massive_source.py:42-49, 124-129`; `backend/app/market/massive_parse.py:38-51`
**Issue:** Not changed by 05-04. On the free tier, `start()` makes 1 `get_snapshot_all` call (403) and then up to 5 `get_grouped_daily_aggs` calls. For example, after a Monday holiday it requests Tue (403), Mon, Sun, Sat, then Fri, all in the same second. Every EOD poll walks back over the same days again. The CR-01 path adds more calls. With an empty start, the first `add_ticker` makes 2 calls (a single-snapshot 403, then the previous close). `_bars` stays empty until the next poll, so every other add in that window costs one more previous-close call.

`RESTClient(api_key=key)` keeps the SDK defaults: `retries=3`, and `status_forcelist` includes 429, with a 0.1 s backoff (`massive/rest/base.py:61-73`). Each 429 is retried almost at once, which burns more of the quota. When the retries run out, urllib3 raises `MaxRetryError`, not `BadResponse`. The step-back in `latest_grouped_bars` never sees it, so the whole poll fails and the next try comes 900 s later.
**Fix:** Build the client with `RESTClient(api_key=key, retries=0)`. Cache the trading day that was resolved and only walk back again after it changes. If the first EOD poll fails, retry after a short delay (for example 60 s) instead of waiting the full 900 s.

### WR-02: Lifespan blocks on Massive network I/O before the app serves (still present)

**File:** `backend/app/main.py:49`; `backend/app/market/massive_source.py:42-49`
**Issue:** Not changed. `start()` still awaits `_poll_once()` inline. With the SDK defaults (10 s connect timeout, 10 s read timeout, 3 retries) and up to 6 calls in a row, a slow or unreachable API can hold startup for minutes. During that time `/api/health` does not answer and no UI is served.
**Fix:** Let the loop task do the first poll, so `start()` returns at once:
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
At minimum, pass a shorter `connect_timeout`/`read_timeout` to `RESTClient`.

### WR-03: An invalid API key logs a traceback on every poll and shows nothing in the UI (still present)

**File:** `backend/app/market/massive_source.py:63-67, 135-141`; `backend/app/api/health.py:14`
**Issue:** Not changed. A wrong or revoked key returns 401 "Unknown API Key", which is not `NOT_AUTHORIZED`. The error is re-raised and logged with `logger.exception` every 15 s, forever, and on every `add_ticker` call. The cache stays empty, so every trade fails with "No price available", yet `/api/health` still returns `{"status": "ok", "source": "massive"}`.
**Fix:** Log `BadResponse` as a one-line `logger.error("Massive poll failed: %s", e)` and keep `logger.exception` for unexpected errors. Optionally, keep a `last_error` on the source and show it in health.

### WR-04: The cache version bumps on every poll, so the frontend appends duplicate sparkline points (still present)

**File:** `backend/app/market/massive_source.py:131-133`; `frontend/src/lib/usePriceStream.ts:64-68`
**Issue:** Not changed. Each poll rewrites every ticker, even when nothing moved. EOD bars stay the same all day, and snapshots do not move after hours. Each write bumps `PriceCache.version`, so SSE sends a full payload, and `history` appends the same price again for every ticker. The sparklines fill with flat duplicate points. `chart` de-duplicates on timestamp, but `history` does not.
**Fix:**
```python
def _write(self, ticker: str, quote: Quote) -> None:
    price, ts, ref = quote
    cur = self._cache.get(ticker)
    if cur and cur.timestamp == ts and cur.price == round(price, 2):
        return
    self._cache.update(ticker, price, timestamp=ts, reference=ref)
```

### WR-05: A failed first fetch leaves a ticker tracked but unpriced, and `add_ticker` will not retry it (new)

**File:** `backend/app/market/massive_source.py:58-69` (with `backend/app/services.py:29-33`)
**Issue:** `add_ticker` appends the ticker to `_tickers` *before* it fetches. If the fetch raises (transient 5xx, 429/`MaxRetryError`, timeout) or returns `None` (a snapshot with no timestamp, or an empty previous close), the ticker stays tracked with no cache entry. Every later `add_ticker` for it returns early at line 60 without making a call. `place_trade` relies on exactly that call to price a ticker (`if cache.get(ticker) is None: await source.add_ticker(ticker)`). For a watched ticker, which stays tracked after `reconcile_stream`, every trade fails with "No price available" until the next poll succeeds. That is 15 s in snapshot mode and up to 900 s in EOD mode. If the ticker is missing from the grouped bars, it is never priced at all, because the poll never falls back to the previous close.

Reproduced with the test `FakeClient`. `add_ticker("PYPL")` with `single=RuntimeError` failed. After the client was fixed, a second `add_ticker("PYPL")` made **no** client call: `tracked: True cached: None new calls: []`.
**Fix:** Skip the fetch only when the ticker is both tracked and priced:
```python
async def add_ticker(self, ticker: str) -> None:
    if ticker not in self._tickers:
        self._tickers.append(ticker)
    if self._cache.get(ticker):
        return
    try:
        quote = await self._fetch_one(ticker)
    except Exception:
        logger.exception("Massive fetch failed for %s", ticker)
        return
    if quote:
        self._write(ticker, quote)
```
Add a test: a failing first fetch, then a working client, then `add_ticker` again should price the ticker.

## Info

### IN-01: EOD day change is open-to-close, while snapshot mode uses the previous close (still present)

**File:** `backend/app/market/massive_parse.py:33-35`
**Issue:** `bar_quote` uses `bar.open` as the reference, so the meaning of "daily change %" depends on the plan. The CR-01 path makes this worse: a ticker priced from `get_previous_close_agg` shows the open-to-close change of the *previous* day, while tickers from the grouped bars show the latest day.
**Fix:** Document it in the UI, or compute the reference from the previous trading day's close.

### IN-02: `latest_grouped_bars` returns an empty dict when a day has bars but none have a close (still present)

**File:** `backend/app/market/massive_parse.py:48-49`
**Issue:** `if bars:` is checked before the `b.close` filter, so a day whose bars all have a zero close returns `{}` instead of stepping back a day.
**Fix:** `found = {b.ticker: b for b in bars if b.close}; if found: return found`.

### IN-03: A `MASSIVE_POLL_INTERVAL` of 0 or less makes a tight poll loop in snapshot mode (still present)

**File:** `backend/app/market/factory.py:18`
**Issue:** `float("0")` leads to `asyncio.sleep(0)` in snapshot mode. Only EOD mode has a minimum interval (`max(..., EOD_MIN_INTERVAL)`).
**Fix:** `interval = max(1.0, float(...))`.

### IN-04: The "EOD" badge also shows on a paid snapshot plan outside market hours (still present)

**File:** `frontend/src/lib/usePriceStream.ts:61-62`; `frontend/src/components/Header.tsx:35-39`
**Issue:** Staleness is judged only by timestamp age (more than 300 s). After hours on a snapshot plan, the header says "EOD · as of ..." even though the data is not end-of-day bars.
**Fix:** Use a neutral label such as "Delayed · as of ...", or send the source mode to the frontend.

### IN-05: The poll-loop test depends on timing (still present)

**File:** `backend/tests/market/test_massive_source.py:184-194`
**Issue:** The test uses `interval=0.02` and two fixed `sleep(0.06)` windows around `asyncio.to_thread` calls. On a loaded WSL or CI host it can fail now and then.
**Fix:** Poll until the call count goes up, with a generous deadline (for example 1 s).

### IN-06: One single-ticker 403 now switches the whole source to EOD for the rest of the process (new)

**File:** `backend/app/market/massive_source.py:84-91, 97-101`
**Issue:** With 05-04, `_enter_eod()` can also be triggered by `get_snapshot_ticker` for one ticker. Tickers come from user or LLM input (AI chat watchlist adds). If Massive ever returns `NOT_AUTHORIZED` for a single symbol the plan cannot read, while bulk snapshots are allowed, a paid snapshot key would drop to EOD bars with a 900 s interval until restart. I have not confirmed that Massive does this. The switch can never be undone, so the risk is worth noting.
**Fix:** Switch modes only on the bulk `get_snapshot_all` 403. For a single-ticker 403, either fall back to the previous close for that ticker only, or call `get_snapshot_all` once to confirm before calling `_enter_eod()`.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
