---
phase: 03-trading-portfolio
reviewed: 2026-10-19T12:06:34Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - backend/app/api/portfolio.py
  - backend/app/api/schemas.py
  - backend/app/api/watchlist.py
  - backend/app/main.py
  - backend/app/portfolio.py
  - backend/app/snapshots.py
  - backend/app/streaming.py
  - backend/tests/conftest.py
  - backend/tests/test_portfolio.py
  - backend/tests/test_portfolio_api.py
  - backend/tests/test_snapshots.py
  - backend/tests/test_streaming_union.py
  - frontend/src/components/Header.tsx
  - frontend/src/components/Heatmap.tsx
  - frontend/src/components/MainChart.tsx
  - frontend/src/components/Panel.tsx
  - frontend/src/components/PnlChart.tsx
  - frontend/src/components/PositionsTable.tsx
  - frontend/src/components/Terminal.tsx
  - frontend/src/components/TradeBar.tsx
  - frontend/src/components/Watchlist.tsx
  - frontend/src/components/WatchlistAddForm.tsx
  - frontend/src/lib/chartTheme.ts
  - frontend/src/lib/format.ts
  - frontend/src/lib/portfolio.ts
  - frontend/src/lib/treemap.ts
  - frontend/src/lib/usePortfolio.ts
  - frontend/src/lib/useSize.ts
  - test/e2e/helpers.ts
findings:
  critical: 2
  warning: 4
  info: 4
  total: 10
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-19T12:06:34Z
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

I reviewed the Phase 3 changes since 66ea67c: trade execution, the portfolio view, snapshots, reconciliation of the streamed set (watchlist ∪ held), and the trading/portfolio UI. The backend suite passes (96 tests). The single-transaction trade write is sound: `BEGIN IMMEDIATE` plus rollback on any exception, so a rejected trade leaves the database unchanged.

Two money-correctness defects were reproduced with scripts:

1. Each trade's cash amount is rounded to cents, but the share quantity and average cost are not. Small fills therefore cost too little, or nothing, so the user can get free shares and repeat it for profit.
2. Stream reconciliation runs outside the trade lock. When trades on the same ticker run concurrently, the cache entry is dropped and re-seeded at a new random price. The ticker stays held and is marked at a price unrelated to its fill.

Other issues: inconsistent multi-SELECT reads in `portfolio_view`, a 500 response after a trade has already committed, and some frontend robustness gaps.

## Critical Issues

### CR-01: Rounding each trade to cents lets the user get shares free or underpay (money creation)

**File:** `backend/app/portfolio.py:57-58, 70-71`
**Issue:** `amount = round(quantity * price, 2)` is the only value charged or credited. The position, however, receives the full `quantity`, and `avg_cost` is set to the raw `price`. For quantities of 4 decimal places, `quantity * price` often falls below half a cent, or rounds down by up to $0.0049 per trade. This was reproduced against `execute_trade` on a fresh DB:

- 100 buys of 0.0001 ZZZ @ $49.99: cash stays at **$10,000.00** while the position grows to 0.01 shares (free). Selling 0.01 then credits $0.50 (cash 10000.50).
- 100 buys of 0.0001 AAPL @ $149.00: $0.50 is charged for 0.01 shares worth $1.49. The sell credits $1.49, ending with cash at **$10,000.99**.

Any price works if the quantity is chosen to round favourably, and the HTTP API accepts `quantity: 0.0001`. Cost basis also drifts: `avg_cost` claims $149 per share while $50 per share was actually paid, so the displayed P&L is wrong as well.
**Fix:** Reject fills whose rounded amount does not match the economic value. The simplest rule is to reject any trade whose amount rounds to $0 and to charge buys by rounding up (and credit sells by rounding down), so rounding never favours the user:
```python
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

def _amount(side, quantity, price):
    raw = Decimal(str(quantity)) * Decimal(str(price))
    mode = ROUND_CEILING if side == "buy" else ROUND_FLOOR
    return float(raw.quantize(Decimal("0.01"), rounding=mode))

amount = _amount(side, quantity, price)
if amount <= 0:
    raise TradeError("Trade value must be at least $0.01")
```
Alternatively, base `avg_cost` on the cash actually paid (`amount / quantity`) so P&L stays honest. Add a regression test for repeated micro-buys.

### CR-02: Stream reconcile runs outside the trade lock, so a concurrent trade re-seeds a held ticker at a random price

**File:** `backend/app/api/portfolio.py:136-151`, `backend/app/streaming.py:44-49`, `backend/app/api/watchlist.py:57-62`
**Issue:** `reconcile_stream` checks the DB (`is_watched_or_held`) in a thread and then calls `source.remove_ticker` afterwards. All of this happens in a `finally` outside `trade_lock`. Trade A fails (or sells out) on an unwatched ticker while trade B buys the same ticker:

1. A's reconcile sees "not held" and calls `remove_ticker`, which clears the cache and the simulator state.
2. B commits its buy.
3. B's reconcile calls `add_ticker`, which re-seeds the ticker at `uniform(50, 300)`.

Reproduced 20 out of 20 times with `asyncio.gather` of a failing 1,000,000-share buy and a 1-share buy on a new ticker. The position is filled at one price and immediately marked at an unrelated one, for example QHXX filled at 73.89 and marked at 283.59 (+284% instant P&L that can be sold for real cash). A narrower interleaving (check before B's commit, remove after B's add) leaves a held ticker not streaming at all, so it is marked at `avg_cost` indefinitely. `DELETE /api/watchlist/{t}` racing a buy of `t` hits the same path. A trade can also spuriously fail with "No price available" when another request's reconcile removes the ticker between the pre-lock `add_ticker` and the locked `cache.get`.
**Fix:** Serialize the whole check-and-mutate under the same lock, and do the pre-trade `add_ticker` inside it too:
```python
async with request.app.state.trade_lock:
    try:
        if cache.get(body.ticker) is None:
            await source.add_ticker(body.ticker)
        ...execute...
    finally:
        await reconcile_stream(source, body.ticker)
```
Take the same lock in the watchlist DELETE (and POST) around the DB write plus reconcile. You could also pass the lock to `reconcile_stream`.

## Warnings

### WR-01: A snapshot failure after a committed trade returns 500, and the UI tells the user to retry

**File:** `backend/app/api/portfolio.py:148`, `frontend/src/lib/usePortfolio.ts:48-49`
**Issue:** The trade commits inside `execute_trade`, then `record_snapshot` runs. If the snapshot raises (DB locked, disk full), the request returns 500 even though cash and the position already changed. The frontend maps any non-400/422 result to "Could not place the trade. Try again." and does not refresh, so a retry places a second trade.
**Fix:** Make the post-trade snapshot best-effort, as `snapshot_loop` already is:
```python
try:
    await asyncio.to_thread(snapshots.record_snapshot, cache)
except Exception:
    logger.exception("post-trade snapshot failed")
return result
```
On the frontend, call `refresh()` on any non-OK result so displayed cash reflects reality.

### WR-02: `portfolio_view` reads cash and positions in two separate autocommit reads, so snapshots can be torn

**File:** `backend/app/portfolio.py:85-89` (also used by `snapshots.record_snapshot`)
**Issue:** With Python's default sqlite3 transaction handling, each SELECT runs in autocommit, so cash and positions come from different read snapshots. Neither `snapshot_loop` nor `GET /api/portfolio` takes the trade lock. A trade that commits between the two SELECTs gives a total that is off by the full trade value: post-trade cash with pre-trade positions on a buy, or the reverse. That value is persisted as a snapshot and shows as a spike or dip in the P&L chart.
**Fix:** Wrap both reads in one read transaction:
```python
with closing(connect(db_path())) as conn:
    conn.execute("BEGIN")
    cash = ...
    rows = ...
    conn.commit()
```

### WR-03: Trade quantity parser accepts hex and exponent strings

**File:** `frontend/src/components/TradeBar.tsx:29-30`
**Issue:** `Number(quantity.trim())` accepts `"0x10"` (16), `"0b11"` (3) and `"1e3"` (1000). A user who mistypes can place a much larger order than intended, with no confirmation step. The 4-decimal check passes for all of these.
**Fix:** Validate the text before converting: `if (!/^\d+(\.\d{1,4})?$|^\.\d{1,4}$/.test(quantity.trim())) return setError(BAD_QTY);`

### WR-04: Positions table re-sorts by live market value on every tick, so rows move under the cursor

**File:** `frontend/src/lib/portfolio.ts:40`, `frontend/src/components/PositionsTable.tsx:51`
**Issue:** `derivePositions` sorts by `market_value`, which is recomputed from SSE quotes about every 500 ms. When two positions have similar values, rows swap back and forth, so a click can land on (and select) the wrong ticker. Row focus also jumps when using the keyboard.
**Fix:** Sort the table by a stable key (backend order or ticker), and sort by value only inside `Heatmap` for the treemap layout.

## Info

### IN-01: Each trade bumps `version` twice, causing two history fetches and an interval restart

**File:** `frontend/src/lib/usePortfolio.ts:38-39`
**Issue:** `refresh()` already increments `version`, and the explicit `setVersion` adds a second bump. `PnlChart` runs its effect twice. The `seq` guard makes this harmless, but it is redundant.
**Fix:** Remove line 39, or stop bumping in `refresh` and bump only after trades.

### IN-02: An out-of-range quantity gets a misleading error message

**File:** `frontend/src/lib/usePortfolio.ts:44-47`
**Issue:** Quantities above 1,000,000 (the backend `le=1_000_000`) return 422 and show "Enter a quantity above 0 (up to 4 decimals)."
**Fix:** Mention the maximum in the message, or check it client-side.

### IN-03: Silent refresh failure after a successful trade leaves cash stale

**File:** `frontend/src/lib/usePortfolio.ts:14-18`
**Issue:** `refresh` swallows all errors. After a successful trade, a failed refetch leaves the header cash and the positions showing pre-trade values with no indication.
**Fix:** Expose an error state, or retry once.

### IN-04: `test_snapshot_loop` cancels the task without awaiting it

**File:** `backend/tests/test_snapshots.py:52-57`
**Issue:** `task.cancel()` is not followed by an awaited cancellation. A `to_thread` snapshot that is still running can outlive the test and its temporary DB.
**Fix:** `with suppress(asyncio.CancelledError): await task` after cancelling.

---

_Reviewed: 2026-10-19T12:06:34Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
