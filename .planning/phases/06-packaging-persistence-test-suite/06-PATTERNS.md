# Phase 6: Packaging, Persistence & Test Suite - Pattern Map

**Mapped:** 2026-10-20
**Files analyzed:** 17 (new or modified)
**Analogs found:** 15 / 17 (vitest config/setup have no in-repo analog; use RESEARCH.md examples)

Note: Dockerfile, docker-compose.yml, scripts/*, .env.example, test/docker-compose.test.yml and specs 01-06 already exist. Per RESEARCH they are verify-and-fix only, not rewritten.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `frontend/src/components/Terminal.tsx` (mod: responsive grid) | component | request-response | itself (lines 33-51) | exact |
| `frontend/src/components/ChatDock.tsx` (mod: collapsed-on-mount, overlay, `chat-toggle`) | component | event-driven | itself; mount-effect pattern in Terminal.tsx 24-32 | exact |
| `frontend/src/components/Header.tsx` (mod: `app-header`, `hidden lg:inline`) | component | request-response | itself | exact |
| `frontend/src/components/Watchlist.tsx` (mod: `testId="watchlist"`) | component | request-response | `PositionsTable.tsx` line 26 (`Panel testId="positions"`) | exact |
| `frontend/src/components/Sparkline.tsx` + `WatchlistRow.tsx` (mod: `sparkline-{T}`, `max-lg:opacity-100`) | component | transform | `PriceCell.tsx` (`"price-" + ticker` testid) | exact |
| `frontend/src/components/PositionsTable.tsx` (mod: `position-qty-{T}`, `position-pnl-{T}`) | component | request-response | itself, `heatmap-cell` `data-pnl` convention | exact |
| `frontend/vitest.config.ts`, `frontend/vitest.setup.ts` (new) | config | n/a | none (use RESEARCH.md Code Examples); alias mirrors `tsconfig.json` paths | none |
| `frontend/package.json` (mod: `test` script, devDeps) | config | n/a | existing scripts block | exact |
| `frontend/src/lib/portfolio.test.ts`, `format.test.ts` (new) | test | transform | `lib/portfolio.ts` (pure functions under test) | role-match |
| `frontend/src/components/PriceCell.test.tsx` (new) | test | event-driven | `PriceCell.tsx` effect lines 20-35 | role-match |
| `frontend/src/components/Watchlist.test.tsx`, `PositionsTable.test.tsx`, `Header.test.tsx` (new) | test | CRUD | props in `Watchlist.tsx` 24-46 | role-match |
| `frontend/src/components/ChatDock.test.tsx` (new) | test | request-response | `ChatDock.tsx`; `useChat` mocked via `vi.mock` | role-match |
| `test/e2e/07-responsive.spec.ts` (new) | test (E2E) | request-response | `test/e2e/01-fresh-start.spec.ts` + `helpers.ts openApp` | exact |
| `test/e2e/01-fresh-start.spec.ts`, `03-trading.spec.ts` (mod: use new testids) | test (E2E) | request-response | themselves | exact |
| `test/persistence.sh` (new) | script | batch | `scripts/start_mac.sh` + `stop_mac.sh` | role-match |
| `backend/tests/market/test_source.py` (mod: fix flaky test) | test | event-driven | itself, lines 9-26 | exact |
| `backend/tests/test_routes_smoke.py` (new, only for gaps) | test | request-response | `backend/tests/test_health.py` + `conftest.py` `client` fixture | exact |

## Pattern Assignments

### `Terminal.tsx` (component, responsive layout)

Current code (lines 34, 36, 38, 43) to extend with breakpoint variants. Tailwind 4 defaults: `lg`=1024, `xl`=1280; `max-lg:` variants need no config.

```tsx
<div className="flex h-full flex-col gap-2 p-2">                                   // line 34 -> add max-lg:overflow-y-auto
<div className="grid min-h-0 flex-1 grid-cols-[minmax(320px,28%)_1fr_auto] gap-2"> // line 36
<div className="grid min-h-0 min-w-0 grid-rows-[1.4fr_auto_1fr] gap-2">             // line 38
<div className="grid min-h-0 grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)_minmax(0,1fr)] gap-2"> // line 43
```
Target for line 36 (RESEARCH): `grid-cols-[minmax(240px,30%)_1fr_48px] lg:grid-cols-[minmax(240px,26%)_1fr_48px] xl:grid-cols-[minmax(320px,28%)_1fr_auto]`. Line 43 below `lg`: 2 columns, Positions `max-lg:col-span-2` (render order Heatmap, Positions, Pnl; use `max-lg:order-*` to put Positions first). Add `min-w-0` on every grid child and `max-lg:min-h-[240px]` on panels.

Mount-effect pattern for setState in effect (lines 24-32; copy the eslint disable comment):
```tsx
useEffect(() => {
  ...
  // eslint-disable-next-line react-hooks/set-state-in-effect
  setSelected(next);
}, [rows, loading, selected, portfolio]);
```

### `ChatDock.tsx` (component, event-driven)

Current state and root (lines 29, 55-59):
```tsx
const [collapsed, setCollapsed] = useState(false);
<aside data-testid="chat-panel" data-collapsed={collapsed ? "true" : "false"}
  className={"flex min-h-0 flex-col border border-border bg-surface " + (collapsed ? "w-12" : "w-[360px]")}>
```
Change: `useState(false)` is wrong for the wide default, so initial collapsed must not read `window` in the initializer (static export prerender). Pattern: keep SSR-safe default, then in a mount effect `setCollapsed(!window.matchMedia("(min-width: 1280px)").matches)` with the same `// eslint-disable-next-line react-hooks/set-state-in-effect` comment. Overlay is CSS-only when expanded: `max-xl:absolute max-xl:inset-y-0 max-xl:right-0 max-xl:z-10 max-xl:w-[360px]`; the parent cell must be `relative w-12` at `max-xl`. Add `data-testid="chat-toggle"` to the existing toggle button (lines 64-70); keep `aria-expanded` and the existing `aria-label`s.

### `Header.tsx`

Line 19: add `data-testid="app-header"` to `<header ...>`. Lines 35-39: stale badge keeps its element and testid, hide only the text on narrow: wrap text in `<span className="hidden lg:inline">EOD · as of {nyDate(asOf)}</span>` inside the `data-testid="stale-badge"` span.

### `Watchlist.tsx`, `Sparkline.tsx`, `WatchlistRow.tsx`, `PositionsTable.tsx` (testids)

Analog for panel testid, `PositionsTable.tsx` line 26:
```tsx
<Panel title="Positions" testId="positions">
```
Apply in `Watchlist.tsx` line 51: `<Panel title="Watchlist" active testId="watchlist">`.

Analog for dynamic ticker testid, `PriceCell.tsx` lines 38-40 and `WatchlistRow.tsx` line 42 (`"watchlist-row-" + ticker`, string concatenation style):
```tsx
<span ref={ref} data-testid={"price-" + ticker} ...>
```
Sparkline (currently `({ points, up })`, line 16-18): add `ticker` prop and
`<svg data-testid={"sparkline-" + ticker} data-points={points.length} width="64" ...>`; call site `WatchlistRow.tsx` line 67 becomes `<Sparkline ticker={ticker} points={history} up={...} />`. Remove button class (line 78): add `max-lg:opacity-100`.

PositionsTable lines 52, 73, 78 (`color` from `COLORS[pnlState(r.pnl_pct)]`). Map `positive|negative|flat` to `up|down|flat`:
```tsx
const pnl = { positive: "up", negative: "down", flat: "flat" }[pnlState(r.pnl_pct)];
<span role="gridcell" data-testid={"position-qty-" + r.ticker} className="text-right font-mono tabular-nums">{formatQty(r.quantity)}</span>
<span role="gridcell" data-testid={"position-pnl-" + r.ticker} data-pnl={pnl} className={"text-right font-mono tabular-nums " + color}>{formatSignedMoney(r.unrealized_pnl)}</span>
```
Do not rename existing `price-pos-{T}` (PriceCell gets `"pos-" + ticker`).

### `frontend/package.json` and vitest config (config)

Existing scripts (lines 5-10): add `"test": "vitest run"` after `"typecheck": "tsc --noEmit"`. Install via the Windows npm wrapper with cwd under /mnt/c. `vitest.config.ts` / `vitest.setup.ts`: no in-repo analog; copy RESEARCH.md "Code Examples" (react plugin, jsdom, `@` alias to `src` matching `tsconfig.json` `paths`, stubs for `ResizeObserver` and `matchMedia`). `next build` type-checks test files (tsconfig `include` is `**/*.ts(x)`); if friction, exclude `vitest.*` and `**/*.test.*`.

### Frontend unit tests (test, transform / event-driven / CRUD)

**`lib/portfolio.test.ts`**, targets (`portfolio.ts`): `derivePositions(p, quotes)` returns `{rows:null,total:undefined}` for null (line 31); total = cash + sum(market value) (line 44); sorted by prior `market_value` (line 33); live quote overrides `current_price` (line 35). `pnlState` flat when rounded to 0.00 (lines 49-52). `toSeries` last value wins per second, skips out-of-order (lines 55-65). Build `Portfolio`/`Position` fixtures from types at lines 4-19.

**`PriceCell.test.tsx`**: effect sets `data-flash` synchronously and clears after two rAFs (PriceCell.tsx 20-35). Render with `direction={undefined}`, rerender with `price` changed and `direction="up"`, assert `screen.getByTestId("price-AAPL")` has `data-flash="up"` immediately; with `live={false}` assert no `data-flash`.

**`Watchlist.test.tsx`**: props listed at Watchlist.tsx 24-46 (`tickers, quotes, history, status, selected, onSelect, onAdd, onRemove, loading, loadError`). Use `onAdd = vi.fn().mockResolvedValue("Unknown ticker")` then expect `watchlist-add-error` (lines 54-58); click `watchlist-remove-{T}` expects `onRemove("AAPL")`; empty state `watchlist-empty` when `tickers=[]` and not loading (lines 102-106); new `sparkline-AAPL` `data-points`.

**`ChatDock.test.tsx`**: `vi.mock("@/lib/useChat")` returning `{ messages, pending: true, send }` -> `chat-loading` present (ChatDock 115, `Loading` 9-26), `chat-input` disabled (line 128); stub `window.matchMedia` `matches:false` -> `chat-panel` `data-collapsed="true"` and content (`chat-messages`) still in DOM. Note `useChat` loads history on mount (useChat.ts "loads history on mount"), which resolves RESEARCH Open Question 1: reload shows prior messages. Mock `fetch` if testing the real hook.

Do not unit test `MainChart`/`PnlChart` (lightweight-charts canvas); `vi.mock("lightweight-charts")` or skip.

### `test/e2e/07-responsive.spec.ts` (E2E, request-response)

**Analog:** `test/e2e/01-fresh-start.spec.ts` and `helpers.ts`.

Imports and flow pattern (01-fresh-start lines 1-2, helpers `openApp` lines 14-18):
```ts
import { expect, test } from "@playwright/test";
import { openApp } from "./helpers";

test("fresh start shows default watchlist and $10,000 cash", async ({ page }) => {
  await openApp(page);
  ...
});
```
`openApp` waits for `connection-status[data-status=connected]` and `cash-balance` containing "$". Copy the loop spec from RESEARCH.md Code Examples (viewports 1280, 1024, 768; `page.setViewportSize` before `openApp`; check `app-header`, `watchlist`, `chat-panel`, `main-chart` visible; `scrollWidth <= innerWidth`). Playwright config default viewport is 1600x1000 (`playwright.config.ts` line 94) so existing specs stay desktop. Spec must be read-only (no state mutation); expanding via `chat-toggle` is allowed. At 1024/768 assert `chat-panel` has `data-collapsed="true"`. Use `expect(...).toHaveAttribute` auto-wait, never sleeps (helpers use `expect.poll`).

Modify 01: add `await expect(page.getByTestId("sparkline-AAPL")).toBeVisible();` after the watchlist row loop (lines 63-66). Modify 03: after line 13 add `await expect(page.getByTestId("position-qty-AAPL")).toBeVisible();`.

### `test/persistence.sh` (script, batch)

**Analog:** `scripts/start_mac.sh` and `stop_mac.sh`.

Header and docker wrapper pattern (start_mac.sh lines 1-6, stop_mac.sh):
```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
DOCKER="${DOCKER:-docker}"
```
Run pattern (start_mac.sh lines 122-127):
```bash
"$DOCKER" rm -f "$CONTAINER" >/dev/null 2>&1 || true
"$DOCKER" run -d --name "$CONTAINER" \
  -v finally-data:/app/db \
  -p 8000:8000 \
  --env-file .env \
  "$IMAGE" >/dev/null
```
Change for the check: container `finally-p`, volume `finally-test-data`, port `8001:8000`, `-e LLM_MOCK=true -e MASSIVE_API_KEY=` (no `--env-file`), so real user data is never touched. Sequence per RESEARCH: remove volume, run, wait on `/api/health` with a curl loop, POST trade/watchlist/chat, `rm -f`, run again on same volume, assert `/api/portfolio` has AAPL qty 2 and PYPL in `/api/watchlist`; chat history persisted (`useChat` loads history, so check via the history/DB read). Cleanup trap removes container and volume. Make executable and record `100755` (`git update-index --chmod=+x`).

### `backend/tests/market/test_source.py` (flaky fix)

Flaky test (lines 9-26): fixture starts `SimulatorDataSource(cache, update_interval=0.02)` so ticks plus 2-5% random events run before the 1% assertion at line 25:
```python
async def test_cache_seeded_before_start_returns(running):
    cache, _ = running
    prices = {t: u.price for t, u in cache.get_all().items()}
    assert set(prices) == set(DEFAULT_TICKERS)
    assert all(abs(prices[t] / SEED_PRICES[t] - 1) < 0.01 for t in prices)
```
Fix per user rule: reproduce first (loop the single test ~50x), then make the test not race the loop (e.g. build the source with a long `update_interval` for this test, or assert directly after `start` with a source whose loop has not ticked). Do not loosen tolerance.

### `backend/tests/test_routes_smoke.py` (test, request-response)

**Analog:** `backend/tests/test_health.py` (ASGITransport against `app`) and `conftest.py` `client` fixture (lifespan on temp DB).

Pattern from conftest.py lines 17-24:
```python
@pytest.fixture
async def client(db_env):
    async with main.app.router.lifespan_context(main.app):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
```
Test style from test_health.py: plain `async def test_x(client)` with `assert response.status_code == ...` (asyncio auto mode, no decorator). Add only gaps found in the audit: unknown `/api/*` path -> 404, chat 4xx/422 shapes, static mount fallthrough. Note conftest `no_network` autouse guard blocks real LLM calls.

## Shared Patterns

### data-testid conventions
**Source:** `WatchlistRow.tsx` 42, `PriceCell.tsx` 40, `PositionsTable.tsx` 26 and 57.
**Apply to:** all new hooks. Static ids via `Panel testId=`; dynamic ids as `"prefix-" + TICKER` string concatenation (uppercase ticker); state via `data-*` attributes never classes; additive only, no renames.

### SSR-safe client code
**Source:** `Terminal.tsx` 24-32 (state set inside `useEffect` with the eslint-disable comment).
**Apply to:** ChatDock matchMedia read. Never read `window` in a `useState` initializer (static export).

### Docker/script idempotency
**Source:** `scripts/start_mac.sh` 107-127, `stop_mac.sh`.
**Apply to:** `test/persistence.sh`. `set -euo pipefail`, `DOCKER` override, `rm -f ... || true` before `run`, named volume mounted at `/app/db`.

### E2E conventions
**Source:** `test/e2e/helpers.ts`, `playwright.config.ts`.
**Apply to:** 07 spec and edits. Use `openApp`, `expect.poll`, auto-waiting `expect`; no fixed sleeps; serial, single shared app state; new specs numbered after 06 and must not mutate defaults.

### Backend tests
**Source:** `backend/tests/conftest.py`.
**Apply to:** route smoke tests. Use `client` fixture, `db_env` temp DB, `MASSIVE_API_KEY=""`, `no_network` guard. Run with `cd backend && uv run pytest -q -x`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/vitest.config.ts` | config | n/a | No test runner exists in the frontend; use RESEARCH.md Code Examples |
| `frontend/vitest.setup.ts` | config | n/a | Same; stubs for ResizeObserver and matchMedia come from RESEARCH.md |

(Also no frontend test file exists to copy; the test files above are modeled on the components under test plus RESEARCH.md's test plan.)

## Metadata

**Analog search scope:** `frontend/src/{components,lib}`, `test/`, `scripts/`, `backend/tests`
**Files scanned:** about 20 read in full or part (git ls-files listing of whole repo reviewed)
**Pattern extraction date:** 2026-10-20
