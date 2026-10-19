# Phase 4: AI Chat Copilot - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning

<domain>
## Phase Boundary

User chats with FinAlly, which analyzes the portfolio and executes trades and watchlist changes on request. Delivers: `POST /api/chat` (complete JSON reply, structured output, auto-executed actions, persisted history), `GET /api/chat/history`, deterministic mock mode (`LLM_MOCK=true`), and the chat dock UI with loading state, inline action confirmations and portfolio/watchlist refresh after actions. Requirements: CHAT-01..09, UI-11, TEST-03.

Not in this phase: Massive (Phase 5), Docker/tablet/frontend unit tests (Phase 6).

AI integration phase (AI-SPEC.md) skipped by user decision: framework fixed by PLAN.md and `.claude/skills/cerebras/SKILL.md`; evaluation is covered by mock-mode tests.

</domain>

<decisions>
## Implementation Decisions

### LLM call and prompt
- Use `litellm.acompletion` (async; the event loop and SSE stream never block, CHAT-09) with exactly the skill's settings: `model="openrouter/openai/gpt-oss-120b"`, `extra_body={"provider": {"order": ["cerebras"]}}`, `reasoning_effort="low"`, `response_format=ChatResponse`, then `ChatResponse.model_validate_json(content)`. `uv add litellm python-dotenv` (pydantic already present)
- `ChatResponse` (pydantic): `message: str`, `trades: list[{ticker, side: buy|sell, quantity}] = []`, `watchlist_changes: list[{ticker, action: add|remove}] = []`
- Messages: a "FinAlly, an AI trading assistant" system prompt per PLAN.md section 9 (analyze composition/risk/P&L, suggest trades with reasoning, execute when asked or agreed, manage watchlist proactively, concise and data-driven, always valid structured JSON); a fresh portfolio context block each turn (cash, total value, positions with qty/avg cost/price/P&L, watchlist with live prices); the last 20 stored chat messages; then the new user message
- The backend loads `.env` from the repo root at startup via python-dotenv (does not override already-set env vars). `LLM_MOCK=true` switches to the mock; `OPENROUTER_API_KEY` is read by LiteLLM
- Malformed JSON / validation failure or any LLM/API error: return 200 with a friendly assistant error message and no actions (CHAT-07); the user message and the error reply are both stored. No retries

### Action execution
- Order: watchlist changes first, then trades (so "add PYPL and buy 5" works). Both reuse the existing code paths under `app.state.trade_lock`: trades go through the same validation, execution, `reconcile_stream` and post-trade snapshot as `POST /api/portfolio/trade`; watchlist add/remove use the same DB + source logic as the watchlist routes. Extract shared service functions rather than calling routes over HTTP
- Each action produces a record `{type: "trade"|"watchlist", ticker, side|action, quantity?, price?, ok: bool, error?: str}`; the list is returned in the response and stored as JSON in `chat_messages.actions` for the assistant message (null for user messages)
- `POST /api/chat {message}` returns `{message: {id, role: "assistant", content, actions, created_at}}` (complete JSON, no streaming, CHAT-01); empty/oversized input -> 422 (cap ~2000 chars)
- Failed AI trades are explained inline: action chips inside the assistant bubble show the server reason (e.g. "Insufficient cash: need $X, have $Y"). No second LLM call
- Mock mode (`LLM_MOCK=true`): deterministic, no network. Regex on the user text for `(buy|sell) <qty> <TICKER>` and `(add|remove) <TICKER>`; reply content starts with "Mock response:" (E2E `05-chat.spec.ts` checks this) and the parsed actions execute through the same path; any other text gets a plain "Mock response: ..." reply with no actions

### Chat UI
- The existing collapsible 360px chat dock becomes the "FinAlly AI" panel: scrolling message list (auto-scroll to bottom on new messages), single-line input and purple (`#753991`) Send button; Enter sends. Test ids per E2E: `chat-panel`, `chat-input`, `chat-send`, `chat-message` with `data-role` user|assistant, `chat-action` with `data-ok` true|false (contains the ticker), `chat-loading`
- While a request is pending: a `chat-loading` typing bubble is shown and the input/send are disabled; `chat-loading` is removed when the reply arrives
- `GET /api/chat/history` returns the last 50 messages oldest-first so history survives reloads (small addition to the PLAN.md API table)
- After any reply with actions, refresh portfolio, watchlist and P&L history (UI-12, via the existing `usePortfolio` version and `useWatchlist` load)
- Fold in Phase 3 UI-audit priority fixes: Enter in the trade bar submits Buy; selection stays on a ticker after it is sold out (no jump to AAPL); heatmap cells get a visible selected style and `role="button"` with `aria-pressed`

### Claude's Discretion
- Module layout (`app/chat/` package vs modules), prompt wording details, context block format (compact text or JSON), chat message bubble styling within existing UI-SPEC tokens

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/portfolio.py` (`execute_trade`, `portfolio_view`, `TradeError`), `backend/app/api/portfolio.py` trade route (lock, add_ticker, reconcile, snapshot), `backend/app/api/watchlist.py` (add/remove under lock), `backend/app/api/schemas.py` (`Ticker`, `Quantity` validators), `backend/app/streaming.py`, `backend/app/snapshots.py`, `backend/app/db.py`; `chat_messages` table already exists in `backend/db/schema.sql`
- `backend/tests/conftest.py` lifespan + tmp DB fixture
- Frontend: `ChatDock.tsx` (collapsible shell), `usePortfolio` (version/refresh), `useWatchlist` (load, seq guard), `TradeBar`, `Heatmap`, `Terminal`, `Panel`, `format.ts`

### Established Patterns
- Router factories with full `/api/...` paths; pydantic validation -> 422; DB via `asyncio.to_thread`; money-moving work under `app.state.trade_lock`
- Verification on ports 8024+ with scratch DB_PATH and `LLM_MOCK=true`; stop by explicit PID; `node`/`npm` are Windows wrappers (WSLENV for env vars)

### Integration Points
- `test/e2e/05-chat.spec.ts` (mocked chat trade with inline action), `helpers.ts`
- `.claude/skills/cerebras/SKILL.md` is the source of truth for the LLM call

</code_context>

<specifics>
## Specific Ideas

- Prior-build pitfall: the async chat handler did blocking sqlite calls. All DB access from the chat path goes through `asyncio.to_thread`, and the LLM call is `acompletion`
- Unit tests must never call the real API: tests use mock mode or monkeypatch `acompletion` (valid JSON, malformed JSON, exception)
- One optional live smoke with the real `OPENROUTER_API_KEY` (from `.env`) at the phase gate, if the key works; it is not a gate requirement

</specifics>

<deferred>
## Deferred Ideas

- Token-by-token streaming (out of scope by PLAN.md)
- AI-SPEC / eval suite (skipped by user)

</deferred>
