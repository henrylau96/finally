# Phase 4: AI Chat Copilot - Research

**Researched:** 2026-10-19
**Domain:** LiteLLM -> OpenRouter -> Cerebras structured output, FastAPI async service refactor under a non-reentrant lock, chat persistence, React chat dock
**Confidence:** HIGH (LiteLLM behaviour was verified by experiment in a scratch uv project on Python 3.14, including one real call)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**LLM call and prompt**
- Use `litellm.acompletion` (async; the event loop and SSE stream never block, CHAT-09) with exactly the skill's settings: `model="openrouter/openai/gpt-oss-120b"`, `extra_body={"provider": {"order": ["cerebras"]}}`, `reasoning_effort="low"`, `response_format=ChatResponse`, then `ChatResponse.model_validate_json(content)`. `uv add litellm python-dotenv` (pydantic already present)
- `ChatResponse` (pydantic): `message: str`, `trades: list[{ticker, side: buy|sell, quantity}] = []`, `watchlist_changes: list[{ticker, action: add|remove}] = []`
- Messages: a "FinAlly, an AI trading assistant" system prompt per PLAN.md section 9 (analyze composition/risk/P&L, suggest trades with reasoning, execute when asked or agreed, manage watchlist proactively, concise and data-driven, always valid structured JSON); a fresh portfolio context block each turn (cash, total value, positions with qty/avg cost/price/P&L, watchlist with live prices); the last 20 stored chat messages; then the new user message
- The backend loads `.env` from the repo root at startup via python-dotenv (does not override already-set env vars). `LLM_MOCK=true` switches to the mock; `OPENROUTER_API_KEY` is read by LiteLLM
- Malformed JSON / validation failure or any LLM/API error: return 200 with a friendly assistant error message and no actions (CHAT-07); the user message and the error reply are both stored. No retries

**Action execution**
- Order: watchlist changes first, then trades (so "add PYPL and buy 5" works). Both reuse the existing code paths under `app.state.trade_lock`: trades go through the same validation, execution, `reconcile_stream` and post-trade snapshot as `POST /api/portfolio/trade`; watchlist add/remove use the same DB + source logic as the watchlist routes. Extract shared service functions rather than calling routes over HTTP
- Each action produces a record `{type: "trade"|"watchlist", ticker, side|action, quantity?, price?, ok: bool, error?: str}`; the list is returned in the response and stored as JSON in `chat_messages.actions` for the assistant message (null for user messages)
- `POST /api/chat {message}` returns `{message: {id, role: "assistant", content, actions, created_at}}` (complete JSON, no streaming, CHAT-01); empty/oversized input -> 422 (cap ~2000 chars)
- Failed AI trades are explained inline: action chips inside the assistant bubble show the server reason (e.g. "Insufficient cash: need $X, have $Y"). No second LLM call
- Mock mode (`LLM_MOCK=true`): deterministic, no network. Regex on the user text for `(buy|sell) <qty> <TICKER>` and `(add|remove) <TICKER>`; reply content starts with "Mock response:" (E2E `05-chat.spec.ts` checks this) and the parsed actions execute through the same path; any other text gets a plain "Mock response: ..." reply with no actions

**Chat UI**
- The existing collapsible 360px chat dock becomes the "FinAlly AI" panel: scrolling message list (auto-scroll to bottom on new messages), single-line input and purple (`#753991`) Send button; Enter sends. Test ids per E2E: `chat-panel`, `chat-input`, `chat-send`, `chat-message` with `data-role` user|assistant, `chat-action` with `data-ok` true|false (contains the ticker), `chat-loading`
- While a request is pending: a `chat-loading` typing bubble is shown and the input/send are disabled; `chat-loading` is removed when the reply arrives
- `GET /api/chat/history` returns the last 50 messages oldest-first so history survives reloads (small addition to the PLAN.md API table)
- After any reply with actions, refresh portfolio, watchlist and P&L history (UI-12, via the existing `usePortfolio` version and `useWatchlist` load)
- Fold in Phase 3 UI-audit priority fixes: Enter in the trade bar submits Buy; selection stays on a ticker after it is sold out (no jump to AAPL); heatmap cells get a visible selected style and `role="button"` with `aria-pressed`

### Claude's Discretion
- Module layout (`app/chat/` package vs modules), prompt wording details, context block format (compact text or JSON), chat message bubble styling within existing UI-SPEC tokens

### Deferred Ideas (OUT OF SCOPE)
- Token-by-token streaming (out of scope by PLAN.md)
- AI-SPEC / eval suite (skipped by user)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | `POST /api/chat` returns one complete JSON response | Route shape below; `acompletion` non-streaming |
| CHAT-02 | Prompt = system prompt + portfolio context + history | Prompt assembly pattern; context from `portfolio_view` + `db.list_watchlist` + cache |
| CHAT-03 | LiteLLM -> OpenRouter gpt-oss-120b via Cerebras, structured output | Verified: LiteLLM turns the pydantic class into strict `json_schema`; live call succeeded |
| CHAT-04 | LLM trades auto-execute with the same validation; failures reported | `services.place_trade` shared by route and chat; per-action `ok/error` |
| CHAT-05 | Watchlist changes auto-execute | `services.add_to_watchlist` / `remove_from_watchlist` |
| CHAT-06 | Messages and actions stored in `chat_messages` | `chat_store` with `to_thread`, one transaction per turn |
| CHAT-07 | Malformed output handled gracefully | Catch `ValidationError` and any `Exception` around the LLM call -> friendly 200 |
| CHAT-08 | `LLM_MOCK=true` deterministic mock incl. a trade | Regex mock; read env at call time |
| CHAT-09 | Chat does not block the event loop | `acompletion` verified non-blocking (max loop gap 52-136 ms during a 2 s call); pytest proof pattern below |
| UI-11 | Collapsible chat panel with loading and inline confirmations | ChatDock/useChat pattern; test ids from context |
| TEST-03 | Backend pytest covers parsing, malformed, trade validation in chat flow | Validation Architecture section |
</phase_requirements>

## Summary

LiteLLM 1.106.0 (PyPI, current) installs cleanly into the existing Python 3.14 project without changing fastapi, pydantic, uvicorn or httpx versions (verified by resolving a copy of the lockfile). Passing a pydantic class as `response_format` to `acompletion` for `openrouter/openai/gpt-oss-120b` works exactly as the skill states: LiteLLM itself converts the class into `{"type":"json_schema","json_schema":{"name":"ChatResponse","strict":true,"schema":{...}}}`, adds `additionalProperties:false` to every object, and lists every property (including fields that have defaults, like `trades`) under `required`. So `list[...] = []` defaults in the pydantic model are safe; no manual schema is needed. `extra_body={"provider":{"order":["cerebras"]}}` is merged to the top-level request body as `provider`, and `reasoning_effort="low"` is sent as top-level `reasoning_effort`. One real call (OPENROUTER_API_KEY present in `.env`) returned valid JSON that `ChatResponse.model_validate_json` parsed into the expected trade and watchlist change.

Three operational traps were found by experiment: (1) `import litellm` fetches a model-cost JSON from raw.githubusercontent.com unless `LITELLM_LOCAL_MODEL_COST_MAP=True` is in the environment before import (confirmed with an httpx hook: 1 request without, 0 with), and import costs about 3 s either way; (2) the default `litellm.request_timeout` is 6000 s, so a hung provider would leave the UI spinner forever unless `timeout=` is passed; (3) LiteLLM prints a noisy "Give Feedback / Get Help" banner on exceptions unless `litellm.suppress_debug_info = True`.

The backend refactor is straightforward: move the lock-taking bodies of the trade and watchlist routes into async service functions that each acquire `trade_lock` themselves; routes and the chat executor both call them one at a time, and the LLM call happens outside any lock. This avoids re-entrancy by construction.

**Primary recommendation:** Add `app/services.py` (lock-owning trade/watchlist functions raising `TradeError`/`WatchlistError`), `app/chat/` (schema, llm, mock, prompt, store, route), keep the LLM call outside the lock, and prove CHAT-09 with a pytest that runs a slow fake `acompletion` while asserting `cache.version` advances and an event-loop ticker shows no gap above ~300 ms.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM call, prompt assembly, parsing | API / Backend | - | Key must stay server-side; structured output validated in Python |
| Action execution (trades, watchlist) | API / Backend | Database | Same validation and lock as manual flow; atomic SQLite writes |
| Chat history persistence | Database / Storage | API / Backend | `chat_messages` table already exists |
| Mock mode | API / Backend | - | Switch inside the backend; frontend is unaware |
| Chat panel UI, loading state, chips | Browser / Client | - | Static export; talks to `/api/chat*` same origin |
| Refresh after actions | Browser / Client | API / Backend | Client re-fetches portfolio/watchlist/history via existing hooks |
| Stream continuity during LLM call | API / Backend (event loop) | - | `acompletion` + `to_thread` keep loop free |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | 1.106.0 | `acompletion` to OpenRouter | Mandated by PLAN.md/skill [VERIFIED: PyPI json + experiment, 2026-10-19] |
| python-dotenv | 1.2.4 | Load repo-root `.env`, `override=False` default | Mandated by CONTEXT [VERIFIED: PyPI] |
| pydantic | 2.14.1 (already via fastapi) | `ChatResponse` model, request model | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest / pytest-asyncio / httpx | existing | Backend tests (asyncio_mode=auto) | All chat tests; no new test deps |

### Alternatives Considered
Not applicable: stack is locked by CONTEXT.md.

**Installation (from `backend/`):**
```bash
~/.local/bin/uv add litellm python-dotenv
```
Resolution result in a scratch copy of the project lock: adds litellm 1.106.0, python-dotenv 1.2.4, pydantic-settings 2.16.0, pydantic-core 2.50.1 and transitives (openai 2.54.0, tiktoken, tokenizers); fastapi 0.146.0, httpx 0.28.1, uvicorn 0.54.0 unchanged [VERIFIED: uv add on a copy].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| litellm | PyPI | multi-year, 1.106.0 current | very high | github.com/BerriAI/litellm | [OK] | Approved |
| python-dotenv | PyPI | multi-year, 1.2.4 | very high | github.com/theskumar/python-dotenv | [OK] (note: "python-" prefix pattern, established package) | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none. Both names are mandated by the user-approved skill and CONTEXT.

## Architecture Patterns

### System Architecture Diagram

```
Browser ChatDock --POST /api/chat {message}--> chat route (422 if empty/>2000)
                                                  |
             +------------------------------------+
             v
  to_thread: portfolio_view + watchlist + load last 20 messages   (no lock)
             |
             v
   LLM_MOCK? --yes--> mock.respond(text) (regex) ----------------+
             |no                                                  |
             v                                                    |
   await acompletion(..., timeout=30)  (event loop free; SSE continues)
             |  exception / ValidationError -> friendly error reply, actions=[]
             v                                                    |
        ChatResponse <-------------------------------------------+
             |
             v   sequential, each call takes trade_lock itself, never nested
   for wl in watchlist_changes: services.add/remove  -> action record
   for t in trades:             services.place_trade -> action record (+ snapshot after lock)
             |
             v
  to_thread: INSERT user msg + assistant msg(actions JSON) in one transaction
             |
             v
  200 {message:{id,role,content,actions,created_at}} --> client: refresh portfolio, watchlist, P&L
```

### Recommended Project Structure
```
backend/app/
  services.py          # place_trade / add_to_watchlist / remove_from_watchlist (own the lock)
  api/portfolio.py     # trade route -> services.place_trade, map TradeError -> 400
  api/watchlist.py     # add/remove routes -> services
  chat/
    __init__.py
    schema.py          # ChatResponse, TradeAction, WatchlistChange, ChatRequest (len 1..2000)
    llm.py             # MODEL consts, complete(messages) -> ChatResponse (the ONLY acompletion call site)
    mock.py            # respond(text) -> ChatResponse (regex)
    prompt.py          # SYSTEM_PROMPT, build_messages(context, history, text)
    store.py           # save_turn, recent(limit), history(limit) - sync sqlite helpers
    execute.py         # run_actions(app, cache, source, resp) -> list[dict]
    router.py          # create_chat_router(cache, source)
backend/tests/test_chat_*.py
frontend/src/components/ChatDock.tsx (+ ChatMessage.tsx), frontend/src/lib/useChat.ts
```

### Pattern 1: LiteLLM structured call (verified)
```python
# Source: experiment 2026-10-19 (litellm 1.106.0) + .claude/skills/cerebras/SKILL.md
import os
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")   # BEFORE import litellm
import litellm
from litellm import acompletion
litellm.suppress_debug_info = True

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

async def complete(messages: list[dict]) -> ChatResponse:
    r = await acompletion(model=MODEL, messages=messages, response_format=ChatResponse,
                          reasoning_effort="low", extra_body=EXTRA_BODY, timeout=30)
    return ChatResponse.model_validate_json(r.choices[0].message.content or "")
```
Notes:
- Request body observed on the wire: `response_format.json_schema.strict=true`, `additionalProperties:false` on `ChatResponse`, `Trade`, `W`; `required` lists all properties even those with defaults; `provider` and `reasoning_effort` top-level; model sent as `openai/gpt-oss-120b`. `litellm.supports_response_schema(MODEL)` is True and `reasoning_effort` is in `get_supported_openai_params` [VERIFIED: experiment].
- `OPENROUTER_API_KEY` is read from the environment by LiteLLM; no key passing needed.
- Define `ChatResponse` leniently: `ticker: str`, `quantity: float`, `side: Literal["buy","sell"]`, `action: Literal["add","remove"]`. Do NOT use the `Ticker`/`Quantity` validators in the LLM schema: one bad ticker would fail the whole parse and lose the message (CHAT-07 fallback). Validate each action individually instead (below).
- The model returned pretty-printed JSON, content was valid, `finish_reason=stop` in the live call [VERIFIED: one real call; outcome recorded in Sources].
- `content` can be `None` (e.g. truncated reasoning); `or ""` turns that into a `ValidationError` handled as malformed output.

### Pattern 2: Lock-owning service functions (no re-entrancy)
```python
# app/services.py  (bodies lifted from the current routes)
class WatchlistError(Exception): ...

async def place_trade(app, cache, source, ticker, side, quantity) -> dict:
    async with app.state.trade_lock:
        try:
            if cache.get(ticker) is None:
                await source.add_ticker(ticker)
            update = cache.get(ticker)
            if update is None:
                raise TradeError(f"No price available for {ticker}")
            result = await asyncio.to_thread(portfolio.execute_trade, ticker, side, quantity, update.price)
        finally:
            await reconcile_stream(source, ticker)
    try:
        await asyncio.to_thread(snapshots.record_snapshot, cache)   # outside the lock, best effort
    except Exception:
        logger.exception("post-trade snapshot failed")
    return result
```
Route becomes `try: return await services.place_trade(...) except TradeError as e: raise HTTPException(400, str(e)) from e` (existing tests assert the 400 messages, which stay identical). `add_to_watchlist` returns `(row, created)`; `remove_from_watchlist` raises `WatchlistError("Ticker not on watchlist")` (route maps to 404). Rule: service functions take the lock; callers never hold it. The chat executor therefore runs actions one by one with no outer lock, which is both deadlock-free and keeps manual trades responsive. Do not wrap the whole action batch in one lock: it would require a lock-free inner variant and double the code paths.

### Pattern 3: Per-action validation, never fail the whole turn
```python
async def run_actions(app, cache, source, resp) -> list[dict]:
    actions = []
    for w in resp.watchlist_changes:            # watchlist first
        actions.append(await _watchlist(app, cache, source, w))
    for t in resp.trades:
        actions.append(await _trade(app, cache, source, t))
    return actions

async def _trade(app, cache, source, t):
    rec = {"type": "trade", "ticker": t.ticker, "side": t.side, "quantity": t.quantity, "ok": False}
    try:
        req = TradeRequest(ticker=t.ticker, side=t.side, quantity=t.quantity)   # reuses Ticker/Quantity rules
        out = await services.place_trade(app, cache, source, req.ticker, req.side, req.quantity)
        rec |= {"ticker": req.ticker, "quantity": req.quantity, "price": out["trade"]["price"], "ok": True}
    except (ValidationError, TradeError) as e:
        rec["error"] = str(e) if isinstance(e, TradeError) else "Invalid trade (ticker 1-5 letters, quantity > 0, max 4 decimals)"
    return rec
```
Adding an already-watched ticker should be `ok: true` (idempotent). Removing a ticker not on the list is `ok: false, error: "X is not on your watchlist"`. Cap the number of actions per reply (for example first 10) to bound lock time.

### Pattern 4: Prompt assembly
`[system prompt] + [system: "Current portfolio state (live)" compact text] + history (last 20, oldest first) + [user text]`. Build history for the LLM from stored rows; for assistant rows with actions append a one-line summary (e.g. `[executed: bought 3 AAPL @ 190.12; failed: sell 5 TSLA - Cannot sell 5 TSLA; you hold 0]`) so the model does not repeat or deny prior actions. Load history BEFORE saving the new user message so the new text is not duplicated. Compact text context is recommended (cheaper, clearer than JSON). Instruct the model that quantity is a number of shares and tickers are uppercase 1-5 letters, and that it should leave `trades` empty when only advising.

### Pattern 5: Persistence (single transaction per turn)
`store.save_turn(user_text, assistant_text, actions_json)` inserts both rows in one `with closing(connect(db_path())) as conn, conn:` block. Use `datetime.now(UTC).isoformat()` for the user message captured at request start and a fresh one for the assistant. Read with `ORDER BY rowid` (ties on `created_at` are possible); `history` uses the same `SELECT ... FROM (... ORDER BY rowid DESC LIMIT ?) ORDER BY r` pattern as `snapshots.history`. Parse `actions` with `json.loads` on read (null for user rows). Both called via `asyncio.to_thread`.

### Pattern 6: Dotenv and LLM_MOCK
In `main.py`, before importing `app.chat` (which imports litellm):
```python
from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")      # override=False by default; missing file is silent
```
Read `os.environ.get("LLM_MOCK", "").lower() == "true"` at request time (not import time) so tests can `monkeypatch.setenv`. In Docker `.env` is passed via `--env-file`, so the dotenv path simply does not exist there: harmless.

### Anti-Patterns to Avoid
- Holding `trade_lock` across the LLM call: blocks manual trades for seconds.
- Nested `async with trade_lock` (asyncio.Lock is not reentrant: deadlock). Never call a route handler or a lock-taking service from inside the lock.
- Sync `completion` or direct sqlite calls in the handler (the prior-build pitfall).
- Using `Ticker`/`Quantity` validators inside the LLM response model.
- Calling the service layer from a background task without a request (not needed here; pass `request.app`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema for structured output | A hand-written json_schema dict | Pass the pydantic class as `response_format` | LiteLLM emits strict schema with `additionalProperties:false` and all-required (verified) |
| Trade validation for AI trades | A second validator | `TradeRequest` + `portfolio.execute_trade` via `services.place_trade` | Identical rules, atomic, already tested |
| Env loading | Manual `.env` parsing | `python-dotenv` `load_dotenv` | Handles quoting, no override |
| Timeouts | Manual `asyncio.wait_for` | `acompletion(timeout=30)` | Cancels the HTTP call properly |
| Chat history ordering/pagination | Custom cursors | Existing subquery pattern from `snapshots.history` | Consistent with codebase |

## Common Pitfalls

### Pitfall 1: LiteLLM network call and cost on import
**What goes wrong:** `import litellm` GETs `raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` (offline/CI or Docker without egress hangs or logs warnings); import takes ~3 s and slows app and test startup.
**Why:** remote model-cost map is the default. **Avoid:** `os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP","True")` before the first import (verified 1 request -> 0). To keep pytest start fast, import litellm only in `chat/llm.py` and import that module lazily inside the function or accept ~3 s once. Prefer top-level import in `llm.py` with the env set at the top of that module (so any import order is safe), and keep `litellm` out of `app.main` imports other than via the chat router.
**Warning signs:** `requests`/httpx call to githubusercontent at startup.

### Pitfall 2: Default timeout is 6000 s
**What goes wrong:** a stuck provider holds the request (and the disabled UI) for 100 minutes. **Avoid:** `timeout=30`. Timeout raises `litellm.Timeout` (subclass of the openai errors); handled by `except Exception`.

### Pitfall 3: Exceptions
Connection failure raised `litellm.exceptions.APIConnectionError` (MRO: `APIError`, `OpenAIError`); `AuthenticationError`, `RateLimitError`, `Timeout`, `BadRequestError` share the same base family [VERIFIED: experiment]. A missing `OPENROUTER_API_KEY` is NOT detected locally (no pre-network error was raised), so it surfaces from OpenRouter as an HTTP error (`AuthenticationError`) after a network round trip. Catch `Exception` broadly around the LLM call (CONTEXT: any error -> friendly message), `logger.exception` the details, never echo the exception text (may contain request info) to the user. LiteLLM also prints a decorated banner to stderr on errors; set `litellm.suppress_debug_info = True`.

### Pitfall 4: `asyncio.Lock` deadlock
See Pattern 2. A test with a 1 s timeout (`asyncio.wait_for`) around a chat request that executes a trade plus a watchlist add guards against re-entrancy.

### Pitfall 5: First-call loop hiccup
Measured max event-loop gap during a slow (2 s) call: 136 ms on the first call (lazy init inside litellm), 52 ms afterwards. Well below the 500 ms SSE cadence. Optional: warm up not needed.

### Pitfall 6: Trade bar Enter does nothing (UI audit item)
Root cause: the form has two text inputs and no `type="submit"` button (Buy/Sell are `type="button"`), and HTML implicit submission requires a submit button when there is more than one text field, so `onSubmit` never fires on Enter. Fix: make the Buy button `type="submit"` and drop its `onClick` (the form `onSubmit` already calls `submit("buy")`); Sell stays `type="button"`.

### Pitfall 7: Selection jump after sell-out
`Terminal.tsx` effect re-selects AAPL when `selected` is not in `watchlist + positions`. After selling out a non-watched ticker it vanishes from both. Fix: keep `selected` unless the user removes it from the watchlist while not held, or track `selected` as user intent and only fall back when the selection was never valid. Note: `reconcile_stream` stops streaming such a ticker, so its chart goes stale; acceptable and consistent with the decision.

### Pitfall 8: Double refresh bump
`usePortfolio.trade` calls `refresh()` and `setVersion` again. For chat, call `refresh()` only (it already bumps `version`, which reloads `PnlChart`), plus `useWatchlist().load()`. Expose `load` is already returned by `useWatchlist`.

### Pitfall 9: Stale response ordering in UI
Disable input while pending (per CONTEXT) so only one request is in flight. Append the user bubble optimistically, and on fetch failure show a local assistant-style error bubble (not stored). On mount fetch `/api/chat/history` once.

### Pitfall 10: Tests must not hit the network or the real `.env`
`load_dotenv` runs when `app.main` is imported by `conftest`, loading the real key into the test process. Add an autouse fixture that monkeypatches `app.chat.llm.acompletion` to raise `AssertionError("network call in test")`; individual tests then override it with fakes. Tests for mock mode use `monkeypatch.setenv("LLM_MOCK","true")`; for LLM-path tests use `setenv("LLM_MOCK","false")` explicitly because `.env` supplies `false`.

## Code Examples

### Mock responder (deterministic)
```python
# app/chat/mock.py
import re
TRADE = re.compile(r"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+([A-Za-z]{1,5})\b", re.I)
WATCH = re.compile(r"\b(add|remove)\s+([A-Za-z]{1,5})\b", re.I)

def respond(text: str) -> ChatResponse:
    trades = [Trade(ticker=m[3].upper(), side=m[1].lower(), quantity=float(m[2])) for m in TRADE.finditer(text)]
    changes = [WatchlistChange(ticker=m[2].upper(), action=m[1].lower()) for m in WATCH.finditer(text)]
    detail = "; ".join([f"{t.side} {t.quantity:g} {t.ticker}" for t in trades] +
                       [f"{c.action} {c.ticker}" for c in changes])
    return ChatResponse(message=f"Mock response: {detail or 'no actions'}", trades=trades, watchlist_changes=changes)
```
Pitfall: "add 5 AAPL" must not parse as a watchlist add of "5"; the `[A-Za-z]` class prevents that. Reply must start with `Mock response` (E2E checks `toContainText("Mock response")`).

### Chat route
```python
class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]

@router.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> dict:
    ctx, history = await asyncio.gather(
        asyncio.to_thread(build_context, cache), asyncio.to_thread(store.recent, 20))
    try:
        resp = mock.respond(body.message) if mock_enabled() else await llm.complete(
            prompt.build_messages(ctx, history, body.message))
    except Exception:
        logger.exception("chat LLM call failed")
        resp = ChatResponse(message="Sorry, I could not process that. Please try again.")
    actions = await run_actions(request.app, cache, source, resp)
    row = await asyncio.to_thread(store.save_turn, body.message, resp.message, actions)
    return {"message": row}
```
`ValidationError` from `model_validate_json` is a subclass of `Exception`, so malformed JSON takes the same branch. The existing app-level `RequestValidationError` handler already returns 422 for empty/oversized input.

### CHAT-09 proof test (pattern)
```python
async def test_stream_continues_during_slow_llm(client, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    async def slow(**kw):
        await asyncio.sleep(1.6)
        return fake_response('{"message":"ok","trades":[],"watchlist_changes":[]}')
    monkeypatch.setattr("app.chat.llm.acompletion", slow)
    gaps, stop = [], asyncio.Event()
    async def ticker():
        last = time.perf_counter()
        while not stop.is_set():
            await asyncio.sleep(0.02); now = time.perf_counter(); gaps.append(now - last); last = now
    t = asyncio.create_task(ticker())
    v0 = main.cache.version
    resp = await client.post("/api/chat", json={"message": "hello"})
    stop.set(); await t
    assert resp.status_code == 200
    assert main.cache.version - v0 >= 2          # simulator ticks every 0.5 s while the call is pending
    assert max(gaps) < 0.3                       # loop never blocked
```
`fake_response` can be `types.SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=...))])`. Negative control (optional, proves the test is sensitive): a fake that uses `time.sleep(1.0)` makes `max(gaps)` fail. Because `llm.complete` accesses `acompletion` as a module global, `monkeypatch.setattr("app.chat.llm.acompletion", ...)` is the single patch point.

### Frontend hook sketch
`useChat({ onActions })`: state `{messages, pending}`; `send(text)` pushes optimistic user message, `POST /api/chat`, appends `data.message`, calls `onActions()` when `actions.length > 0`; Terminal passes `onActions={() => { void refresh(); void load(); }}` using `refresh` from `usePortfolio` and `load` from `useWatchlist`. Auto-scroll with a `ref` and `useEffect` on `[messages, pending]`. Render a chip per action with `data-testid="chat-action" data-ok={String(a.ok)}`, text like `Bought 1 AAPL @ $190.12` / `Failed: sell 5 TSLA - <error>`. Heatmap cell: add `role="button"`, `aria-pressed={selected}`, `tabIndex=0`, key handler and a visible selected style (currently `role="img"`, `data-selected` exists).

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Hand-written json_schema dicts | Pass pydantic class to `response_format`; LiteLLM makes strict schema | Less code; defaults are made required automatically |
| Sync `completion` | `acompletion` | Required for CHAT-09 |

## Runtime State Inventory
Not a rename/refactor phase. Omitted. (`chat_messages` table already exists in `schema.sql`; no migration.)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Cerebras provider via OpenRouter remains available for gpt-oss-120b during the phase gate | Pattern 1 | Live smoke fails; unit tests unaffected. If so, error path is exercised |
| A2 | Missing key yields `AuthenticationError` from OpenRouter (not tested with real endpoint, only inferred: LiteLLM did not raise locally) | Pitfall 3 | None: broad `except Exception` covers any class |
| A3 | Capping actions at 10 per reply is acceptable | Pattern 3 | Low; planner may drop the cap |

## Open Questions

1. **How does a failed LLM call reach the user text-wise?** RESOLVED by CONTEXT: friendly 200 reply, stored with the user message, no retries.
2. **Should actions block while another request holds the lock?** RESOLVED: each action awaits the lock normally; no outer lock.
3. **Unknown tickers (e.g. "ZZZZ") under the simulator:** `SimulatorSource.add_ticker` accepts any ticker and creates a price, so an AI buy of an invented ticker succeeds. Same as the manual flow in Phase 3; not a Phase 4 concern. Mention in the system prompt that only real US tickers should be used.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | install, pytest | yes | ~/.local/bin/uv | - |
| Python | backend | yes | 3.14.4 | - |
| litellm / python-dotenv | chat | to be added | 1.106.0 / 1.2.4 resolve on 3.14 | - |
| OPENROUTER_API_KEY in `.env` | live smoke only | yes (non-placeholder, length 73) | - | mock mode / skip smoke |
| node/npm/npx (Windows wrappers) | frontend lint/typecheck/build, Playwright | yes per context | - | - |
| Network to openrouter.ai | live smoke only | yes (one call succeeded) | - | not required for gates |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio 1.4.0 (asyncio_mode=auto), httpx ASGITransport; Playwright (test/) |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && ~/.local/bin/uv run pytest tests/test_chat_*.py -q` |
| Full suite command | `cd backend && ~/.local/bin/uv run pytest -q` (100 tests pass today, ~4 s) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | POST returns `{message:{id,role,content,actions,created_at}}`; empty/2001-char -> 422 | integration | `uv run pytest tests/test_chat_api.py -q` | Wave 0 |
| CHAT-02 | Messages passed to `acompletion` contain system prompt, portfolio/watchlist context, <=20 history, user text last (capture kwargs in fake) | unit | `uv run pytest tests/test_chat_prompt.py -q` | Wave 0 |
| CHAT-03 | Fake `acompletion` receives `model`, `extra_body`, `reasoning_effort="low"`, `response_format is ChatResponse`, `timeout`; valid JSON parsed | unit | `uv run pytest tests/test_chat_llm.py -q` | Wave 0 |
| CHAT-04 | AI buy ok; insufficient cash / oversell / invalid ticker -> `ok:false` with server error, nothing persisted for that trade; same result as REST | integration | `uv run pytest tests/test_chat_actions.py -q` | Wave 0 |
| CHAT-05 | Watchlist add/remove via chat; add-then-buy in one reply works; duplicate add ok; remove missing -> ok false | integration | `uv run pytest tests/test_chat_actions.py -q` | Wave 0 |
| CHAT-06 | Both rows stored; assistant `actions` JSON round trips; `GET /api/chat/history` last 50 oldest-first, survives re-read | integration | `uv run pytest tests/test_chat_store.py -q` | Wave 0 |
| CHAT-07 | Fake returns malformed JSON / `None` content / schema-violating JSON / raises exception -> 200, friendly message, `actions == []`, both messages stored | integration | `uv run pytest tests/test_chat_api.py -k "malformed or error" -q` | Wave 0 |
| CHAT-08 | `LLM_MOCK=true`: "buy 1 AAPL" executes, reply starts "Mock response"; acompletion guard never called; unrelated text -> no actions | integration | `uv run pytest tests/test_chat_mock.py -q` | Wave 0 |
| CHAT-09 | Slow fake `acompletion` (1.6 s): `cache.version` advances >= 2, loop gap < 0.3 s, concurrent `GET /api/health` returns promptly; chat + concurrent manual trade completes within `wait_for` timeout (no deadlock) | integration | `uv run pytest tests/test_chat_nonblocking.py -q` | Wave 0 |
| TEST-03 | Aggregate of the above | unit+integration | `uv run pytest -q` | Wave 0 |
| UI-11 | Panel renders, loading bubble, chips, history on reload, disabled while pending | e2e + static | `cd frontend && npm run lint && npm run typecheck && npm run build`; `cd test && WSLENV=BASE_URL npx playwright test e2e/05-chat.spec.ts` | 05 spec exists (extend) |
| Phase 3 audit fixes | Enter submits Buy; selection kept after sell-out; heatmap `role=button` + `aria-pressed` | e2e | Extend `03-trading.spec.ts` / `04-portfolio-viz.spec.ts`, run regression specs | extend |

Live HTTP smoke (mock): start `cd backend && LLM_MOCK=true DB_PATH=<scratch>/p4.db uv run uvicorn app.main:app --port 8024` (record the PID, stop it by explicit PID, never `pkill -f uvicorn`), then:
`curl -s -X POST localhost:8024/api/chat -H 'content-type: application/json' -d '{"message":"buy 2 AAPL"}'` (expect `ok:true` chip, `Mock response`), `curl -s localhost:8024/api/chat/history`, `curl -s localhost:8024/api/portfolio`, and a 422 check with `{"message":""}`. Playwright regression: `BASE_URL=http://localhost:8024 WSLENV=BASE_URL npx playwright test` from `test/` against that fresh server (it must run with `LLM_MOCK=true`; env vars set in WSL reach uv/python).

Optional live smoke (not a gate): one real call through `llm.complete` with the `.env` key (already done once in this research; see Sources).

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_chat_*.py -q` (backend) or lint+typecheck (frontend)
- **Per wave merge:** full `uv run pytest -q` plus `npm run lint && npm run typecheck && npm run build`
- **Phase gate:** full pytest green, frontend build green, Playwright 05 and regression specs 01-06 green on a fresh mock server

### Wave 0 Gaps
- [ ] `tests/conftest.py`: autouse `no_network` fixture patching `app.chat.llm.acompletion` to raise; helper `fake_completion(content)` returning the SimpleNamespace shape; fixture setting `LLM_MOCK` explicitly
- [ ] `tests/test_chat_*.py` files listed above
- [ ] Framework install: none needed (pytest, pytest-asyncio, httpx present)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2/V3 Auth, Session | no | Single-user, no auth by design |
| V4 Access Control | no | Same |
| V5 Input Validation | yes | Pydantic `ChatRequest` (1..2000), `TradeRequest` re-validation of every LLM-proposed action |
| V6 Cryptography | no | Key read from env only; never logged or returned |
| V7 Error handling/logging | yes | Log exceptions server-side, return generic message; do not echo exception text |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection driving unwanted trades | Tampering | Accepted by design (fake money, auto-execute); per-action validation and action cap still apply |
| LLM returns invalid/huge quantities | Tampering | `Quantity` bounds (0 < q <= 1,000,000, 4 dp) via `TradeRequest` |
| API key leakage | Information disclosure | `.env` gitignored; never log env; do not include exception text in responses |
| Oversized input / DoS | DoS | 2000 char cap, `timeout=30`, one in-flight request enforced by UI, action cap |
| Stored XSS via chat content | Tampering | Render content as React text nodes (no `dangerouslySetInnerHTML`) |

## Sources

### Primary (HIGH confidence)
- Experiments in scratch uv projects (Python 3.12 and 3.14.4), litellm 1.106.0, openai 2.54.0, pydantic 2.14.1: request-body capture via local HTTP server on `api_base` (strict json_schema, provider, reasoning_effort), import cost and network hook, exception classes, event-loop lag during a slow call, default `request_timeout` 6000
- PyPI JSON API: litellm 1.106.0, python-dotenv 1.2.4; slopcheck: both [OK]
- `.claude/skills/cerebras/SKILL.md`, `.planning/phases/04-ai-chat-copilot/04-CONTEXT.md`
- Codebase: `backend/app/**`, `schema.sql`, `tests/conftest.py`, `frontend/src/components/{ChatDock,Terminal,TradeBar,Heatmap}.tsx`, `lib/{usePortfolio,useWatchlist}.ts`, `test/e2e/05-chat.spec.ts`, `helpers.ts`

### Live smoke (recorded outcome)
- One real call with the `.env` key via `acompletion` + `ChatResponse` against `openrouter/openai/gpt-oss-120b` with Cerebras order: succeeded; `finish_reason=stop`; content parsed by `model_validate_json` into 1 trade (AAPL buy 3) and 1 watchlist add (PYPL). Key never printed.

### Secondary / Tertiary
- None; no claim rests on web search alone. LiteLLM official docs were not fetched because behaviour was verified empirically at the installed version.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions and wire format verified
- Architecture: HIGH - derived from the current route code and a lock-ownership rule
- Pitfalls: HIGH - each LiteLLM pitfall reproduced; HTML implicit submission is a spec rule applied to the observed form markup (MEDIUM until the Enter fix is run in E2E)

**Research date:** 2026-10-19
**Valid until:** 2026-11-18 (LiteLLM releases frequently; re-run `uv lock` check before the phase if it slips)
