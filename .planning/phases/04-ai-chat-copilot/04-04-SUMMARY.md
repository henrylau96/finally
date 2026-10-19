---
phase: 04-ai-chat-copilot
plan: 04
subsystem: api
tags: [litellm, openrouter, cerebras, structured-output, pytest]

requires:
  - phase: 04-ai-chat-copilot
    provides: mock chat backend, run_actions executor, chat store (04-01)
provides:
  - Real LiteLLM -> OpenRouter -> Cerebras structured-output chat call
  - Portfolio-grounded prompt with 20-message history
  - Graceful LLM failure handling and no-network test guard
  - CHAT-09 non-blocking proof
affects: [04-05]

tech-stack:
  added: [litellm, python-dotenv]
  patterns:
    - "llm.py is the single acompletion call site; tests patch llm.acompletion"
    - "Autouse guard fails any test reaching the network via pytest.fail"

key-files:
  created:
    - backend/app/chat/llm.py
    - backend/app/chat/prompt.py
    - backend/tests/test_chat_llm.py
    - backend/tests/test_chat_prompt.py
    - backend/tests/test_chat_api.py
    - backend/tests/test_chat_nonblocking.py
  modified:
    - backend/app/chat/router.py
    - backend/app/main.py
    - backend/tests/conftest.py
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "LITELLM_LOCAL_MODEL_COST_MAP set before importing litellm to avoid the import-time network fetch"
  - "Any LLM exception or invalid output yields the fixed FALLBACK text; exception text never returned"

patterns-established:
  - "load_dotenv of repo-root .env at top of main.py, no override"

requirements-completed: [CHAT-02, CHAT-03, CHAT-07, CHAT-09, CHAT-01, TEST-03]

duration: 25min
completed: 2026-10-20
---

# Phase 4 Plan 04: Real LLM Chat Summary

`POST /api/chat` now calls `litellm.acompletion` (gpt-oss-120b via Cerebras, structured `ChatResponse`, timeout 30) with a live portfolio prompt and 20 messages of history, failing gracefully to a fixed message.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 RED tests + no-network guard | 907ecbf | new tests fail on missing `app.chat.prompt`/`llm`; 119 existing pass |
| 2 llm.py, prompt.py, router, dotenv | 7958b86 | 129 tests pass |
| 3 Non-blocking / no-deadlock tests | 195e63f | 131 tests pass |

## Deviations from Plan

None. The optional sensitivity check (blocking `time.sleep` fake) was not run.

## Known Stubs

None. The 04-01 FALLBACK stub is replaced by the real call.

## Self-Check: PASSED

llm.py, prompt.py and four test files exist; commits 907ecbf and 7958b86 present; full pytest 131 passed; non-blocking tests passed on repeated runs.
