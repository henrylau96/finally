---
phase: 04-ai-chat-copilot
fixed_at: 2026-10-20T00:00:00Z
review_path: .planning/phases/04-ai-chat-copilot/04-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-10-20
**Source review:** .planning/phases/04-ai-chat-copilot/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, WR-01, WR-02, WR-03; IN-01 out of scope)
- Fixed: 4
- Skipped: 0

Final gates: `uv run pytest -q` 133 passed; frontend `lint`, `typecheck`, `build` exit 0; E2E against a LLM_MOCK server on port 8030: 01-fresh-start 3 passed, 05-chat + 03-trading 11 passed, 1 skipped (existing "history already exists" guard).

## Fixed Issues

### CR-01: A skipped watchlist action breaks every later live chat turn

**Files modified:** `backend/app/chat/execute.py`, `backend/tests/test_chat_api.py`
**Commit:** a7a3ea7
**Applied fix:** Skipped (over-cap) records now keep the full shape. Watchlist records include `action`. The reviewer's snippet read `item.action` before checking the kind, which raised `AttributeError` for trades (caught by `test_action_cap`), so the code branches on the kind.
**Evidence:** New test `test_skipped_watchlist_action_keeps_next_turn_working` runs two live-LLM turns (fake `acompletion`). Before the fix, the second turn returned FALLBACK because of the `KeyError` in `_action_text`. After the fix, the second turn calls the LLM and returns its reply.

### WR-01: An unexpected error during actions loses the turn and leaves the UI stale

**Files modified:** `backend/app/chat/execute.py`, `backend/tests/test_chat_actions.py`, `frontend/src/lib/useChat.ts`
**Commit:** 8342766
**Applied fix:** `_run_one` wraps each action. An unexpected exception is logged and recorded as a failed action ("Action failed unexpectedly"). Earlier actions are kept, the turn is saved, and the route returns 200. A shared `_failed()` helper builds both the skipped and the unexpected records. In the client, the `catch` path also calls `onActionsRef.current()`, so portfolio and watchlist are refetched.
**Evidence:** New test `test_unexpected_action_error_keeps_turn` patches `services.place_trade` to raise `RuntimeError("database is locked")`. Before the fix, the exception escaped the route. After the fix, the response is 200 with `[watchlist ok, trade failed]` and history holds the user/assistant pair.

### WR-02: A late history response can wipe out a message the user just sent

**Files modified:** `frontend/src/lib/useChat.ts`, `test/e2e/05-chat.spec.ts`
**Commit:** ae1e420
**Applied fix:** History is applied only while the list is still empty: `setMessages(prev => prev.length > 0 ? prev : items)`. Merging was not used because local user entries carry client ids, so a merge would duplicate the user message.
**Evidence:** New E2E test "a late history load keeps a message sent before it". It fetches `/api/chat/history` early, holds the response until after a send, then releases it. It failed before the fix (the sent message disappeared) and passes after.

### WR-03: The E2E test for the pending state cannot fail

**Files modified:** `test/e2e/05-chat.spec.ts`
**Commit:** 9fc7f10
**Applied fix:** `/api/chat` is held with `page.route`. The test asserts that `chat-loading` is visible and `chat-input` is disabled, releases the route, then asserts that loading is gone and the input is enabled.
**Evidence:** The test passes on the real build. As a mutation check, `ChatDock` input `disabled={pending}` was temporarily changed to `disabled={false}` and the frontend rebuilt. The test then failed on `toBeDisabled()`. The change was reverted and the frontend rebuilt.

---

_Fixed: 2026-10-20_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
