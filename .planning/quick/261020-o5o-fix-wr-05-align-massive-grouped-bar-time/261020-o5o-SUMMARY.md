---
phase: quick-261020-o5o
plan: 01
status: complete
requirements: [WR-05]
key-files:
  modified:
    - backend/app/market/massive_parse.py
    - backend/tests/market/test_massive_parse.py
    - backend/tests/market/test_massive_source.py
---

# Quick 261020-o5o: Align Massive grouped bar time (WR-05) Summary

`bar_quote` now returns NY midnight of the bar's session (new `ny_midnight` helper), so EOD and previous-close cache times equal `daily_points` times and the frontend no longer appends a duplicate last close.

## Tests
- RED confirmed first: 5 failures against the old `bar_quote`.
- Backend: `uv run pytest -q` gives 189 passed (188 + 1 new regression test with real 2026-10-16 AAPL timestamps).
- Frontend: `npm test` gives 45 passed (10 files), untouched.

## Deviations
None. `snapshot_quote`, `daily_points`, and `massive_source.py` unchanged.

## Commit
- fix(quick-261020-o5o): see git log (single code commit)
