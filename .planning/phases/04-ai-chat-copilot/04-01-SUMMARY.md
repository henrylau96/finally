---
phase: 04-ai-chat-copilot
plan: 01
subsystem: api
tags: [fastapi, chat, sqlite, pytest, mock-llm]

requires:
  - phase: 03-trading-portfolio
    provides: execute_trade, trade_lock, watchlist routes, snapshots
provides:
  - POST /api/chat and GET /api/chat/history (mock mode)
  - Lock-owning services (place_trade, add_to_watchlist, remove_from_watchlist)
  - run_actions executor re-validating every LLM action
affects: [04-02, 04-03, 04-04]

tech-stack:
  added: []
  patterns:
    - "services own trade_lock; callers never hold it"
    - "Lenient LLM models, strict re-validation via TradeRequest at execution"

key-files:
  created:
    - backend/app/services.py
    - backend/app/chat/__init__.py
    - backend/app/chat/schema.py
    - backend/app/chat/mock.py
    - backend/app/chat/store.py
    - backend/app/chat/execute.py
    - backend/app/chat/router.py
    - backend/tests/test_chat_mock.py
    - backend/tests/test_chat_store.py
    - backend/tests/test_chat_actions.py
  modified:
    - backend/app/api/portfolio.py
    - backend/app/api/watchlist.py
    - backend/app/main.py

key-decisions:
  - "Non-mock branch of POST /api/chat returns a fallback message until 04-04 adds the LiteLLM call"
  - "Watchlist changes run before trades so add-then-buy works"

patterns-established:
  - "Chat actions recorded as {type, ticker, ..., ok, error?} dicts persisted as JSON in chat_messages.actions"

requirements-completed: [CHAT-01, CHAT-04, CHAT-05, CHAT-06, CHAT-08, TEST-03]

duration: 15min
completed: 2026-10-19
---

# Phase 4 Plan 01: Mock Chat Backend Slice Summary

Mock-mode `POST /api/chat` executes trades and watchlist changes through lock-owning shared services with the same validation as the REST routes, persists both turns, and exposes `GET /api/chat/history`.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 RED tests | 667baae | 3 test files, failing on missing `app.chat`; 100 prior tests green |
| 2 Mock chat API | 60a7fc9 | schema, mock, store, router wired in main |
| 3 Services and execution | e945c48 | services.py, routes delegate, run_actions; 119 tests pass |

## Deviations from Plan

None - plan executed as written (plan-checker notes applied: store round-trip test calls `save_turn` directly; services.py has exactly 3 `async with app.state.trade_lock`).

## Known Stubs

- `chat/router.py` non-mock branch returns `FALLBACK` text; intentional, replaced by the LiteLLM call in 04-04.

## Self-Check: PASSED

All created files exist; commits 667baae, 60a7fc9, e945c48 present; full pytest 119 passed.
