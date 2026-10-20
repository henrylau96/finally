---
phase: 03-trading-portfolio
fixed_at: 2026-10-19T00:00:00Z
review_path: .planning/phases/03-trading-portfolio/03-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-10-19
**Source review:** .planning/phases/03-trading-portfolio/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, CR-02, WR-01..WR-04; Info out of scope)
- Fixed: 6
- Skipped: 0

Backend: 100 tests pass (96 before, plus 4 new regression tests). Each new test failed before its fix. Frontend: lint, typecheck and build pass after each frontend fix. There is no frontend unit-test runner, so WR-03 and WR-04 have no automated test. WR-03 was checked with a node script that ran the regex against sample inputs.

## Fixed Issues

### CR-01: Rounding each trade to cents lets the user get shares free or underpay

**Files modified:** `backend/app/portfolio.py`, `backend/tests/test_portfolio.py`
**Commit:** 288c323
**Applied fix:** I fixed the root cause instead of the reviewer's ceil/floor suggestion. Cash now moves by exactly `quantity * price`: the per-trade amount and the new cash balance are no longer rounded. Cash is rounded to 2 dp only in API output (`execute_trade` result and `portfolio_view.cash_balance`). The exploit script now ends at exactly $10,000.00 for both scenarios; before the fix it ended at $10,000.50 and $10,000.99. Regression test: `test_micro_buys_pay_full_value`.
**CONTEXT deviation:** The decision "Cash and prices rounded to 2 dp" becomes "cash stored at full precision, displayed/returned at 2 dp". The existing tests still pass unchanged.

### CR-02: Stream reconcile runs outside the trade lock

**Files modified:** `backend/app/api/portfolio.py`, `backend/app/api/watchlist.py`, `backend/app/streaming.py`, `backend/tests/test_streaming_union.py`
**Commit:** c079975
**Applied fix:** The pre-trade `add_ticker`, the price read, the trade, and `reconcile_stream` now all run inside `app.state.trade_lock`. Watchlist POST (DB insert plus `source.add_ticker`) and DELETE (DB delete plus reconcile) take the same lock. The snapshot stays outside the lock. In `race.py` the fill price differed from the marked price in 20/20 runs before the fix and in 0/20 after. Regression test: `test_concurrent_trades_keep_fill_price`, which passed 5 times in a row.

### WR-01: Snapshot failure after a committed trade returns 500

**Files modified:** `backend/app/api/portfolio.py`, `backend/tests/test_portfolio_api.py`, `frontend/src/lib/usePortfolio.ts`
**Commit:** 9f66d5d
**Applied fix:** The post-trade snapshot is now best-effort: an exception is logged with `logger.exception` and the trade result is still returned. On the frontend, `refresh()` is awaited before returning the generic error, so displayed cash is current after any unexpected failure. Regression test: `test_snapshot_failure_keeps_trade_ok` (500 before the fix, 200 after).

### WR-02: portfolio_view reads cash and positions in separate snapshots

**Files modified:** `backend/app/portfolio.py`, `backend/tests/test_portfolio.py`
**Commit:** 4bdadc5
**Applied fix:** Both SELECTs now run inside one `BEGIN ... commit()` read transaction (the DB uses WAL, so this gives one consistent snapshot). Regression test: `test_portfolio_view_consistent_read` commits a trade between the two reads every time. Before the fix the total was 11000.0 instead of 10000.0.

### WR-03: Trade quantity parser accepts hex and exponent strings

**Files modified:** `frontend/src/components/TradeBar.tsx`
**Commit:** d369f91
**Applied fix:** The quantity text must now match `/^(\d+(\.\d{1,4})?|\.\d{1,4})$/` and be > 0 before `Number()` converts it. This replaced the old float-tolerance check. A node check confirmed that `0x10`, `0b11`, `1e3`, `-1`, `0`, `0.0000`, `1.23456` and `Infinity` are rejected, and `1`, `0.5`, `.25` and `10.1234` are accepted. `5.` (trailing dot) is now rejected.

### WR-04: Positions table re-sorts by live market value on every tick

**Files modified:** `frontend/src/lib/portfolio.ts`
**Commit:** d1c9347
**Applied fix:** `derivePositions` now sorts by the `market_value` from the last portfolio fetch, before marking positions to live quotes. Order changes only on portfolio refresh, not on SSE ticks. The UI-SPEC order (market value descending) is kept. The treemap is unaffected because `squarify` sorts by live value itself. Status: fixed, requires human verification (the UI behavior was not covered by an automated test).

---

_Fixed: 2026-10-19_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
