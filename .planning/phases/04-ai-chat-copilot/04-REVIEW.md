---
phase: 04-ai-chat-copilot
reviewed: 2026-10-20T00:00:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - backend/app/api/portfolio.py
  - backend/app/api/watchlist.py
  - backend/app/chat/__init__.py
  - backend/app/chat/execute.py
  - backend/app/chat/llm.py
  - backend/app/chat/mock.py
  - backend/app/chat/prompt.py
  - backend/app/chat/router.py
  - backend/app/chat/schema.py
  - backend/app/chat/store.py
  - backend/app/main.py
  - backend/app/services.py
  - backend/pyproject.toml
  - backend/tests/conftest.py
  - backend/tests/test_chat_*.py
  - frontend/src/components/ChatDock.tsx
  - frontend/src/components/ChatMessage.tsx
  - frontend/src/components/Heatmap.tsx
  - frontend/src/components/Terminal.tsx
  - frontend/src/components/TradeBar.tsx
  - frontend/src/lib/useChat.ts
  - test/e2e/03-trading.spec.ts
  - test/e2e/04-portfolio-viz.spec.ts
  - test/e2e/05-chat.spec.ts
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-20
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

I reviewed the chat backend (router, LLM call, mock, prompt, execution, store), the services module that the REST routes and chat now share, and the chat UI with its E2E specs. `uv run pytest -q` reports 131 passed.

Several invariants hold:
- **Lock use:** `trade_lock` is only acquired in `services.py`, and no caller holds it when calling those functions, so there is no re-entrant deadlock. Every money-moving path goes through `services.place_trade`.
- **Thread offload:** all chat DB access uses `asyncio.to_thread`.
- **LLM call:** `acompletion` uses the skill's model, `extra_body`, `reasoning_effort` and `response_format`.
- **Error handling:** provider and JSON errors fall back to a 200 reply with no actions.
- **Mock mode:** it never calls `acompletion`.

One reproduced defect is a blocker. A reply that exceeds the action cap with watchlist changes stores an action record without an `action` key. That record crashes prompt building on every later live-LLM turn, and the chat stays broken until the record drops out of the 20-message history window.

## Critical Issues

### CR-01: A skipped watchlist action breaks every later live chat turn

**File:** `backend/app/chat/execute.py:56-60`, `backend/app/chat/prompt.py:49-51`
**Issue:** When there are more than `MAX_ACTIONS` items, a skipped watchlist change is recorded as `{"type": "watchlist", "ticker", "ok": False, "error"}` with no `action` key. `store.save_turn` saves it. On the next turn, `prompt.build_messages` replays history, and `_action_text` evaluates `a['action']`, which raises `KeyError('action')`. That call happens inside the `try` in `router.py:32-36`, so it is swallowed. The user gets the `FALLBACK` "Sorry, I couldn't process that" reply and no LLM call is made. Each failed turn adds 2 more rows, so chat stays broken for about 10 more turns, until the bad row leaves the `history(20)` window.

**Reproduced:** I ran `run_actions` with 11 watchlist adds, then `save_turn`, `history(20)` and `build_messages`. The result was `KeyError('action')`.

Realistic trigger: "add the 11 biggest tech names to my watchlist". The frontend also renders the chip as "Failed: undefined AK." (`ChatMessage.tsx:7`).
**Fix:** Keep the full record shape for skipped items:
```python
if i >= MAX_ACTIONS:
    base = {"type": "watchlist", "ticker": item.ticker, "action": item.action}
    if kind == "t":
        base = {"type": "trade", "ticker": item.ticker, "side": item.side, "quantity": item.quantity}
    out.append({**base, "ok": False, "error": SKIPPED})
```
Also add a test that saves a skipped watchlist action and then sends a non-mock chat turn.

## Warnings

### WR-01: An unexpected error during actions loses the turn and leaves the UI stale

**File:** `backend/app/chat/router.py:37-38`, `frontend/src/lib/useChat.ts:51-56`
**Issue:** `run_actions` only catches `TradeError`, `WatchlistError` and `ValidationError`. Any other exception from `services.*` returns a 500. Examples are `sqlite3.OperationalError: database is locked` from `BEGIN IMMEDIATE` in `execute_trade`, or a market-source `add_ticker` failure. Earlier actions in the same reply have already moved cash and positions, but `save_turn` never runs. The user message and the record of what executed are both lost.

On the client, the `catch` branch shows "Could not reach FinAlly" and never calls `onActions`. Header cash, positions and the watchlist then show stale values even though trades went through.
**Fix:** In the router, wrap `run_actions` so that an unexpected exception still stores the turn with the actions completed so far plus an error note, and still returns 200. At minimum, call `onActionsRef.current()` in the client `catch` path so the portfolio and watchlist are refetched.

### WR-02: A late history response can wipe out a message the user just sent

**File:** `frontend/src/lib/useChat.ts:32-37`
**Issue:** The mount effect calls `setMessages(items)` unconditionally when `/api/chat/history` resolves. If the user sends a message before that fetch resolves (for example by clicking an example prompt, then Send, on a slow first load), `send` appends the local user entry and the reply. The late history response then replaces the whole list. Whether the new turn survives depends on whether the server read history before or after `save_turn`, so the user's message and reply can disappear from the panel. The action chips go with them, although the refresh already ran.
**Fix:** Merge instead of replacing, for example `setMessages(prev => [...items, ...prev.filter(m => !items.some(i => i.id === m.id))])`. Alternatively, skip the history result once a send has started (track it with a ref).

### WR-03: The E2E test for the pending state cannot fail

**File:** `test/e2e/05-chat.spec.ts:79-86`
**Issue:** `ChatDock.submit` clears `draft` immediately, and the Send button is `disabled={pending || !draft.trim()}`. So `expect(chat-send).toBeDisabled()` passes because the draft is empty, whether or not `pending` works. The test never checks `chat-input` while the request is pending, and the mock reply is fast enough that `chat-loading` may never be seen. A regression in the disable-while-pending logic would not be caught.
**Fix:** Delay the response with `page.route("/api/chat", ...)`. Then assert `chat-input` is disabled and `chat-loading` is visible, release the route, and assert both clear.

## Info

### IN-01: The mock watchlist regex treats ordinary words as tickers

**File:** `backend/app/chat/mock.py:9`
**Issue:** `\b(add|remove)\s+([A-Za-z]{1,5})\b` matches ordinary prose. "Can you add some AAPL?" adds the ticker `SOME`, and "remove the risk" tries to remove `THE`. This only affects mock mode (E2E and dev), but it can add stray watchlist rows that make E2E runs order-dependent.
**Fix:** Require an uppercase ticker in the mock, such as `\b(add|remove)\s+([A-Z]{1,5})\b` with the verb matched case-insensitively via `(?i:add|remove)`, or anchor the pattern to the start of the message.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
