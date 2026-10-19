# Phase 4: AI Chat Copilot - Pattern Map

**Mapped:** 2026-10-19
**Files analyzed:** 24 (new + modified)
**Analogs found:** 22 / 24 (no analog: `chat/llm.py`, `chat/mock.py`; RESEARCH.md Pattern 1 and the mock code example apply)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `backend/app/services.py` (new) | service | request-response (lock-owning) | body of `backend/app/api/portfolio.py` trade route + `api/watchlist.py` add/remove | exact (lift) |
| `backend/app/api/portfolio.py` (mod) | route | request-response | itself | exact |
| `backend/app/api/watchlist.py` (mod) | route | CRUD | itself | exact |
| `backend/app/chat/schema.py` (new) | model | transform | `backend/app/api/schemas.py` | role-match |
| `backend/app/chat/store.py` (new) | repository | CRUD | `backend/app/snapshots.py` (`record_snapshot`, `history`) | exact |
| `backend/app/chat/router.py` (new) | route | request-response | `create_portfolio_router` in `api/portfolio.py` | exact |
| `backend/app/chat/execute.py` (new) | service | batch/request-response | `api/portfolio.py` trade route (error mapping) | role-match |
| `backend/app/chat/prompt.py` (new) | utility | transform | `portfolio.portfolio_view` (data source for context) | partial |
| `backend/app/chat/llm.py`, `chat/mock.py` (new) | service | request-response | none | none |
| `backend/app/main.py` (mod) | config | wiring | itself | exact |
| `backend/tests/conftest.py` (mod) | test | fixtures | itself | exact |
| `backend/tests/test_chat_*.py` (new) | test | integration | `tests/test_portfolio_api.py`, `test_watchlist_api.py` | exact |
| `frontend/src/components/ChatDock.tsx` (mod) | component | request-response | itself (shell) + `TradeBar.tsx` (form) | role-match |
| `frontend/src/components/ChatMessage.tsx` (new) | component | render | `Panel.tsx`/`WatchlistRow.tsx` | partial |
| `frontend/src/lib/useChat.ts` (new) | hook | request-response | `lib/usePortfolio.ts`, `lib/useWatchlist.ts` | exact |
| `frontend/src/components/Terminal.tsx` (mod) | component | wiring | itself | exact |
| `frontend/src/components/TradeBar.tsx` (mod) | component | form | itself | exact |
| `frontend/src/components/Heatmap.tsx` (mod) | component | render | itself | exact |
| `frontend/src/app/globals.css` (mod, optional) | config | - | `.status-pulse` block | exact |
| `test/e2e/05-chat.spec.ts` (mod), `03-trading`/`04-portfolio-viz` (extend) | test | e2e | `05-chat.spec.ts` | exact |

## Pattern Assignments

### `backend/app/services.py` (service, lock-owning request-response)

**Analog:** trade route in `backend/app/api/portfolio.py` lines 28-49 and watchlist routes `api/watchlist.py` lines 91-107. Lift bodies verbatim; replace `HTTPException` with domain errors; services take the lock, callers never hold it.

Imports (portfolio.py 3-14):
```python
import asyncio
import logging
from app import portfolio, snapshots
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.streaming import reconcile_stream
logger = logging.getLogger(__name__)
```

Core to lift (portfolio.py 30-49):
```python
async with request.app.state.trade_lock:
    try:
        if cache.get(body.ticker) is None:
            await source.add_ticker(body.ticker)
        update = cache.get(body.ticker)
        if update is None:
            raise HTTPException(400, f"No price available for {body.ticker}")   # -> raise TradeError(...)
        result = await asyncio.to_thread(portfolio.execute_trade, body.ticker, body.side, body.quantity, update.price)
    finally:
        await reconcile_stream(source, body.ticker)
try:
    await asyncio.to_thread(snapshots.record_snapshot, cache)   # outside lock, best effort
except Exception:
    logger.exception("post-trade snapshot failed")
return result
```
Existing `portfolio.TradeError` is already raised by `execute_trade`; route becomes `except TradeError as e: raise HTTPException(400, str(e)) from e` (existing tests assert identical 400 messages).

Watchlist (watchlist.py 93-107):
```python
async with request.app.state.trade_lock:
    row, created = await asyncio.to_thread(db.add_ticker, body.ticker)
    if created:
        await source.add_ticker(body.ticker)
# remove:
    if not await asyncio.to_thread(db.remove_ticker, t):
        raise HTTPException(404, "Ticker not on watchlist")   # -> raise WatchlistError(...); route maps to 404
    await reconcile_stream(source, t)
```
The route's `item(row)` helper stays in the router (merges cache price); `add_to_watchlist` returns `(row, created)`.

---

### `backend/app/chat/store.py` (repository, CRUD)

**Analog:** `backend/app/snapshots.py` lines 1-38.

Imports/insert pattern (16-26):
```python
from contextlib import closing
from datetime import UTC, datetime
from uuid import uuid4
from app.db import connect, db_path
...
with closing(connect(db_path())) as conn, conn:
    conn.execute("INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, 'default', ?, ?)", (str(uuid4()), total, now))
```
Bounded oldest-first read (29-38) — reuse for `history(50)` and `recent(20)`:
```python
rows = conn.execute(
    "SELECT total_value, recorded_at FROM ("
    "SELECT rowid AS r, total_value, recorded_at FROM portfolio_snapshots "
    "WHERE user_id = 'default' ORDER BY rowid DESC LIMIT ?) ORDER BY r", (limit,)).fetchall()
```
Table (`db/schema.sql` 37-44): `chat_messages(id, user_id, role CHECK user|assistant, content, actions TEXT, created_at)`. Insert both rows of a turn in one `with closing(...) as conn, conn:` block; `json.dumps(actions)` on write, `json.loads` on read (null for user rows). Sync helpers; callers use `asyncio.to_thread`.

---

### `backend/app/chat/router.py` (route, request-response)

**Analog:** `backend/app/api/portfolio.py` lines 17-23 (router factory, full `/api/...` paths, `asyncio.to_thread`).
```python
def create_portfolio_router(cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter()
    @router.get("/api/portfolio")
    async def get_portfolio() -> dict:
        return await asyncio.to_thread(portfolio.portfolio_view, cache)
    return router
```
Register in `main.py` (line 174-177 block): `app.include_router(create_chat_router(cache, source))`. Body model `ChatRequest` with `StringConstraints(min_length=1, max_length=2000)`; 422 comes from the existing `RequestValidationError` handler (main.py 167-171). Route skeleton: RESEARCH.md "Chat route" example. Pass `request.app` to `run_actions`.

---

### `backend/app/chat/schema.py` (model)

**Analog:** `backend/app/api/schemas.py` (pydantic `BaseModel` with `Literal`). Per RESEARCH, LLM models must be lenient (`ticker: str`, `quantity: float`, `side: Literal["buy","sell"]`, `action: Literal["add","remove"]`); do NOT use `Ticker`/`Quantity` there:
```python
class TradeRequest(BaseModel):
    ticker: Ticker
    side: Literal["buy", "sell"]
    quantity: Quantity
```
`execute.py` re-validates each action by constructing `TradeRequest(...)` and catching `ValidationError`/`TradeError` per action (RESEARCH Pattern 3). Add watchlist ticker validation with `normalize_ticker`.

---

### `backend/app/chat/prompt.py` (utility, transform)

No close analog. Data for the context block: `portfolio.portfolio_view(cache)` (keys `cash_balance`, `total_value`, `unrealized_pnl`, `positions`), `db.list_watchlist()` + `cache.get(ticker)` (fields `.price`, `.day_change_pct`). Follow RESEARCH Pattern 4 (compact text, history loaded before saving the new user row, action summary line appended to assistant history rows). Run via `asyncio.to_thread`.

---

### `backend/app/chat/llm.py` and `chat/mock.py` (no analog)

Use RESEARCH Pattern 1 (set `LITELLM_LOCAL_MODEL_COST_MAP` before `import litellm`, `litellm.suppress_debug_info = True`, `acompletion` as a module global so tests patch `app.chat.llm.acompletion`, `timeout=30`) and the "Mock responder" example. Read `LLM_MOCK` at call time.

---

### `backend/app/main.py` (mod)

Add `from dotenv import load_dotenv; load_dotenv(Path(__file__).parents[2] / ".env")` before imports of `app.chat` (existing `Path` import at line 116; imports at 123-128 are alphabetical `from app...`). Add router include after line 177. Lifespan already sets `app.state.trade_lock = asyncio.Lock()` (line 152).

---

### `backend/tests/test_chat_*.py` and `conftest.py`

**Analog:** `tests/test_portfolio_api.py` (module-level helper + async tests using `client`), `tests/conftest.py` fixtures `db_env`, `client`, `seed_position`.
```python
async def trade(client, **body):
    return await client.post("/api/portfolio/trade", json=body)

async def test_insufficient_cash_api(client):
    r = await trade(client, ticker="AAPL", side="buy", quantity=1000000)
    assert r.status_code == 400 and r.json()["detail"].startswith("Insufficient cash")
```
`conftest.py` additions (RESEARCH Pitfall 10): autouse fixture patching `app.chat.llm.acompletion` to raise; `fake_completion(content)` returning `SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=...))])`; tests set `LLM_MOCK` via `monkeypatch.setenv`. Use `main.cache` for stream-continuity assertion (conftest already imports `main`). Keep existing 100 tests green after the services refactor (watchlist and portfolio API tests are the regression net).

---

### `frontend/src/lib/useChat.ts` (hook, request-response)

**Analog:** `frontend/src/lib/usePortfolio.ts` (fetch + seq guard + useCallback) and `useWatchlist.ts`.
```typescript
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
...
const refresh = useCallback(async () => {
  const id = ++seq.current;
  let data = null;
  try { const res = await fetch("/api/portfolio"); if (res.ok) data = await res.json(); } catch {}
  if (id !== seq.current || !data) return;
  ...
}, []);
useEffect(() => { void refresh(); }, [refresh]);   // mount fetch -> use for /api/chat/history
```
POST pattern (usePortfolio.ts 188-192):
```typescript
const res = await fetch("/api/portfolio/trade", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticker, quantity, side }) });
```
Errors: swallow in `try/catch`, return a local error bubble ("Could not reach FinAlly. Try again."). Where an effect sets state, copy the `// eslint-disable-next-line react-hooks/set-state-in-effect` comment (useWatchlist.ts 247). On actions call `onActions` (Terminal passes `refresh` from `usePortfolio` + `load` from `useWatchlist`; call `refresh()` only, not the extra `setVersion` from `trade`; Pitfall 8).

---

### `frontend/src/components/ChatDock.tsx` and `ChatMessage.tsx` (component)

**Analog:** existing `ChatDock.tsx` shell (lines 5-35) keep `data-testid="chat-panel"`, collapse state, chevron SVG and `aria-expanded`; change per UI-SPEC: title "FinAlly AI", content hidden with `hidden` not unmounted, add `data-collapsed`.
```tsx
<aside data-testid="chat-panel" className={"flex min-h-0 flex-col border border-border bg-surface " + (collapsed ? "w-12" : "w-[360px]")}>
  <h2 className="text-xs font-semibold uppercase tracking-[0.05em] text-text-muted">Assistant</h2>
  <button type="button" aria-expanded={!collapsed} aria-label={label} onClick={() => setCollapsed(!collapsed)} className="p-1 text-text-muted hover:text-text">
```
Form/input/button classes from `TradeBar.tsx`:
```tsx
const input = "h-8 border border-border bg-bg px-2 font-mono text-sm uppercase disabled:cursor-progress disabled:opacity-50";  // drop font-mono/uppercase for chat (14px sans)
<form data-testid="trade-bar" aria-busy={pending} onSubmit={(e) => { e.preventDefault(); void submit("buy"); }}>
<button ... className="h-8 w-14 bg-submit text-sm font-semibold text-text hover:brightness-110 disabled:cursor-progress disabled:opacity-50">   // Send: w-16, type="submit"
onKeyDown={(e) => { if (e.key !== "Escape") return; setQuantity(""); ... }}   // Esc clears draft
```
Chip formatting: `formatPrice`, `formatQty` from `@/lib/format`. Typing dots: `className="status-pulse"` with inline `animationDelay` 0/150/300ms (globals.css 26-39). Colors via existing tokens (`bg-bg`, `border-border`, `text-up`, `text-down`; `color-mix` for tints). Render text as React text nodes only.

---

### `frontend/src/components/TradeBar.tsx` (mod: Enter submits Buy)

Per UI-SPEC fold-in #1 (authoritative, differs from RESEARCH Pitfall 6): add `onKeyDown` to BOTH inputs: `if (e.key === "Enter") { e.preventDefault(); void submit("buy"); }`; extend the existing quantity handler (lines 119-123, currently Escape only). Buttons stay `type="button"`.

### `frontend/src/components/Terminal.tsx` (mod)

- Selection effect (lines 309-317): assign default only when `selected` is empty; drop the `valid.includes(selected)` check.
- Destructure `refresh` from `usePortfolio()` (line 306) and `load` from `useWatchlist()` (line 305); pass to `<ChatDock onActions={() => { void refresh(); void load(); }} />` (line 334).

### `frontend/src/components/Heatmap.tsx` (mod)

Cell (lines 43-50): change `role="img"` to `role="button"`, add `aria-pressed={row.ticker === selected}`, add `data-[selected=true]:shadow-[inset_0_0_0_2px_var(--color-primary)]`; keep `tabIndex={0}`, `data-selected`, existing Enter/Space handlers.

### `test/e2e/05-chat.spec.ts` (mod/extend)

Keep as written (uses `openApp`, `readNumber`, `heldQuantity` from `helpers.ts`; locators `[data-testid="chat-message"][data-role="..."]`). Add cases for Enter-submits-Buy to `03-trading.spec.ts`, selection-after-sell-out, heatmap `aria-pressed` to `04-portfolio-viz.spec.ts`, using the same helper imports.

## Shared Patterns

### DB access off the event loop
**Source:** `api/portfolio.py` line 22, `snapshots.py` line 46. `await asyncio.to_thread(sync_fn, args)` for every sqlite call; sync helpers use `with closing(connect(db_path())) as conn, conn:`. **Apply to:** all of `chat/store.py`, `prompt` context build, services.

### Money-moving work under `app.state.trade_lock`
**Source:** `api/portfolio.py` 30, `api/watchlist.py` 93/104. `asyncio.Lock` is not reentrant; services acquire it, callers and the chat executor never hold it; LLM call is outside any lock.

### Best-effort side effects
**Source:** `api/portfolio.py` 45-48 (`try ... except Exception: logger.exception(...)`) and `logger = logging.getLogger(__name__)`. **Apply to:** post-trade snapshot, LLM failure branch (log, return friendly text, never echo exception).

### Validation to 422
**Source:** `main.py` 167-171 `RequestValidationError` handler + pydantic `Ticker`/`Quantity` in `api/schemas.py`. **Apply to:** `ChatRequest`; per-action re-validation with `TradeRequest`.

### Frontend conventions
`"use client"` first line, `@/lib/...` alias imports, fetch with swallowed `catch {}` and sequence-guard refs, `data-testid` on every testable element, Tailwind token classes (`bg-surface`, `border-border`, `text-text-muted`, `text-up/down`, `bg-submit`).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/app/chat/llm.py` | service | external API call | No existing outbound LLM/HTTP client; use RESEARCH Pattern 1 and `.claude/skills/cerebras/SKILL.md` |
| `backend/app/chat/mock.py` | utility | transform | New; use RESEARCH "Mock responder" example |

## Metadata

**Analog search scope:** `backend/app/**`, `backend/tests/**`, `frontend/src/**`, `test/e2e/**`
**Files scanned:** ~60 listed, 14 read
**Pattern extraction date:** 2026-10-19
