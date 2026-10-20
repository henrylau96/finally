---
phase: 4
slug: ai-chat-copilot
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-19
---

# Phase 4 — Validation Strategy

> Per-phase validation contract. Full requirement-to-command map: `04-RESEARCH.md` "Validation Architecture" (authoritative; summarized here).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1 + pytest-asyncio (auto) + httpx ASGITransport; Playwright E2E; eslint + tsc + next build |
| **Config file** | `backend/pyproject.toml`, `test/playwright.config.ts` |
| **Quick run command** | `cd backend && ~/.local/bin/uv run pytest tests/test_chat_*.py -q` |
| **Full suite command** | `cd backend && ~/.local/bin/uv run pytest -q && cd ../frontend && npm run lint && npm run typecheck && npm run build` |
| **Estimated runtime** | ~70 seconds |

---

## Sampling Rate

- **After every task commit:** chat pytest files (backend) or lint + typecheck (frontend)
- **After every plan wave:** full suite command
- **Before `/gsd:verify-work`:** full suite plus Playwright 01 (first, fresh DB), 02-06 on a fresh server started with `LLM_MOCK=true`
- **Max feedback latency:** 70 seconds

---

## Requirement Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| CHAT-01 | POST returns complete message JSON; empty / >2000 chars -> 422 | integration | `uv run pytest tests/test_chat_api.py -q` | ❌ W0 | ⬜ pending |
| CHAT-02 | prompt has system prompt, portfolio + watchlist context, <= 20 history, user last | unit | `uv run pytest tests/test_chat_prompt.py -q` | ❌ W0 | ⬜ pending |
| CHAT-03 | acompletion gets skill model, extra_body, reasoning_effort low, response_format ChatResponse, timeout | unit | `uv run pytest tests/test_chat_llm.py -q` | ❌ W0 | ⬜ pending |
| CHAT-04 | AI trades ok / failed with server reason; failures change nothing | integration | `uv run pytest tests/test_chat_actions.py -q` | ❌ W0 | ⬜ pending |
| CHAT-05 | AI watchlist add/remove; add-then-buy in one reply | integration | `uv run pytest tests/test_chat_actions.py -q` | ❌ W0 | ⬜ pending |
| CHAT-06 | both messages stored; actions JSON round trip; history last 50 oldest-first | integration | `uv run pytest tests/test_chat_store.py -q` | ❌ W0 | ⬜ pending |
| CHAT-07 | malformed / None / schema-violating / exception -> 200 friendly reply, no actions | integration | `uv run pytest tests/test_chat_api.py -k "malformed or error" -q` | ❌ W0 | ⬜ pending |
| CHAT-08 | mock mode deterministic, "Mock response", never calls acompletion | integration | `uv run pytest tests/test_chat_mock.py -q` | ❌ W0 | ⬜ pending |
| CHAT-09 | slow fake LLM: cache version advances, loop gap < 0.3 s, no deadlock with a concurrent trade | integration | `uv run pytest tests/test_chat_nonblocking.py -q` | ❌ W0 | ⬜ pending |
| TEST-03 | all of the above | pytest | `cd backend && uv run pytest -q` | ❌ W0 | ⬜ pending |
| UI-11 | chat panel, loading bubble, chips, history on reload | e2e + static | `cd test && WSLENV=BASE_URL BASE_URL=http://localhost:8024 npx playwright test e2e/05-chat.spec.ts` | ✅ (extend) | ⬜ pending |
| Phase 3 fold-ins | Enter submits Buy; selection kept after sell-out; heatmap role=button + aria-pressed | e2e | extend `03-trading.spec.ts` / `04-portfolio-viz.spec.ts`; run regression | extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Mock smoke (port 8024+, scratch DB, `LLM_MOCK=true`, stop by recorded PID, never `pkill -f uvicorn`): POST `/api/chat` "buy 2 AAPL" -> `ok:true` chip and "Mock response"; GET `/api/chat/history`; `{"message":""}` -> 422.

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py`: autouse fixture making `app.chat.llm.acompletion` raise (no network in tests), `fake_completion(content)` helper, explicit `LLM_MOCK` fixture
- [ ] `backend/tests/test_chat_api.py`, `test_chat_prompt.py`, `test_chat_llm.py`, `test_chat_actions.py`, `test_chat_store.py`, `test_chat_mock.py`, `test_chat_nonblocking.py`
- [ ] `LITELLM_LOCAL_MODEL_COST_MAP=True` set before `import litellm`; `litellm.suppress_debug_info = True`; `timeout=30`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real LLM reply grounded in portfolio | CHAT-02, CHAT-03 | Needs the live API key and judgment | Optional: run without LLM_MOCK, ask "How is my portfolio doing?" |
| Chat UX feel (scroll, chips, loading) | UI-11 | Visual | Human checkpoint at the phase gate |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 70s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
