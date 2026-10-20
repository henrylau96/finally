# Phase 6: Packaging, Persistence & Test Suite - Research

**Researched:** 2026-10-20
**Domain:** Docker packaging, SQLite persistence, responsive CSS, Vitest/RTL frontend tests, Playwright E2E
**Confidence:** HIGH (codebase audited directly); MEDIUM on Vitest 5 toolchain (versions from npm registry, not exercised yet)

## Summary

No CONTEXT.md exists; `planning/PLAN.md` is the spec. The key finding: **most packaging and E2E artifacts already exist** from earlier phases and only need verification and small fixes. Present and working in the repo: multi-stage `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example` (documents all three vars), `.gitignore` (`.env`, `db/*.db`), four start/stop scripts, `test/docker-compose.test.yml`, `test/playwright.config.ts`, six E2E specs (346 lines), and 167 backend tests (166 pass; 1 flaky, see Pitfalls). A `finally:latest` image and a `finally-data` volume already exist locally, and Docker 29.8.1 + Compose v5.5.1 work from WSL. [VERIFIED: codebase + `docker --version`]

The real gaps are: (1) **no frontend test framework at all** (TEST-05: no vitest, no `test` script, no test files); (2) **6 missing `data-testid` hooks** (UI-14); (3) **no responsive behaviour** (UI-13): Terminal.tsx uses a fixed `grid-cols-[minmax(320px,28%)_1fr_auto]`, ChatDock starts expanded, no breakpoints; (4) **no persistence proof** (DATA-04/success criterion 3) -- the volume wiring is right but nothing verifies it; (5) **no backend API-route coverage audit** for TEST-04 (route tests exist per router; need an audit for status codes and error shapes, notably `/api/health`, `/api/stream/prices`, chat 4xx); (6) the E2E compose stack and start/stop scripts have never been proven end-to-end in this phase; add the responsive E2E smoke spec and a persistence check.

**Primary recommendation:** Plan as verification-first: (a) run the existing docker/compose/scripts and fix whatever breaks, (b) add the 6 testids + responsive layout, (c) add Vitest + RTL with a small set of focused tests, (d) add one E2E responsive spec and one persistence script/spec, (e) fix the flaky simulator test.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Static frontend serving | API / Backend (FastAPI `StaticFiles` mount at `/`, last) | CDN/Static (none) | Single origin/port; already in `main.py` |
| Data persistence across restarts | Database / Storage (SQLite on `/app/db` volume) | Docker runtime (named volume) | `DB_PATH` env + volume; lazy `init_db` is idempotent |
| One-command start/stop | Host scripts (Docker CLI wrappers) | — | Scripts only call `docker build/run/rm` |
| Responsive layout / dock overlay | Browser / Client (Tailwind breakpoints + one `matchMedia` read) | — | Pure CSS plus initial collapsed state |
| Test hooks (`data-testid`) | Browser / Client | — | Additive attributes on existing components |
| Frontend component tests | Browser-tier code in jsdom (Vitest) | — | No backend needed; mock fetch/EventSource |
| Backend route tests | API / Backend (pytest + httpx ASGITransport) | — | Existing `client` fixture |
| E2E suite | Playwright container vs app container | — | `test/docker-compose.test.yml`, `LLM_MOCK=true` |

## Standard Stack

### Core (already in place -- do not change)
| Library | Version | Purpose |
|---------|---------|---------|
| Docker multi-stage (`node:20-slim` -> `python:3.14-slim` + `ghcr.io/astral-sh/uv`) | existing | Image build [VERIFIED: Dockerfile] |
| pytest 9.1.1 + pytest-asyncio + httpx | existing in `pyproject.toml` | Backend tests [VERIFIED: pyproject.toml] |
| `@playwright/test` 1.64.1 / image `mcr.microsoft.com/playwright:v1.64.1-noble` | pinned, already pulled locally | E2E [VERIFIED: test/package.json, `docker images`] |

### Supporting (new, frontend devDependencies in `frontend/`)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| vitest | 5.0.5 | Test runner | engines node `^22.12 \|\| ^24 \|\| >=26` [VERIFIED: npm registry]. Local Node is v24, fine. Docker stage uses Node 20: `npm ci` only warns (EBADENGINE) unless engine-strict, and the image never runs vitest. Alternative if the warning is unwanted: `vitest@4.1.x` (supports Node 20) |
| @vitejs/plugin-react | 6.1.2 | JSX transform for vitest | peer vite ^8 [VERIFIED: npm registry] |
| jsdom | 30.1.3 | DOM env | [VERIFIED: npm registry] |
| @testing-library/react | 16.3.3 | render/screen | peer `@testing-library/dom` ^10 must be installed explicitly [VERIFIED: npm registry] |
| @testing-library/dom | ^10 | peer of RTL | install explicitly |
| @testing-library/jest-dom | 7.0.1 | matchers (`toHaveAttribute`) | [VERIFIED: npm registry] |
| @testing-library/user-event | 14.6.8 | typing/clicking | |
| vite | ^8 | peer of vitest 5 / plugin-react 6 | npm 7+ auto-installs peers; add explicitly to be safe |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| jsdom | happy-dom 21 | faster, but jsdom is more faithful for RTL; use jsdom |
| Playwright component tests | — | Unnecessary; PLAN.md says "React Testing Library or similar" |

**Installation (run in `frontend/`, via the Windows npm wrapper, cwd under /mnt/c):**
```bash
npm install -D vitest jsdom @vitejs/plugin-react @testing-library/react @testing-library/dom @testing-library/jest-dom @testing-library/user-event vite
```
Add scripts: `"test": "vitest run"`. Add `vitest.config.ts` (react plugin, `environment: "jsdom"`, `setupFiles: ["./vitest.setup.ts"]`, `resolve.alias "@" -> ./src`, `globals: true` or import explicitly). `vitest.setup.ts`: `import "@testing-library/jest-dom/vitest"`, stub `ResizeObserver` and `matchMedia`, `afterEach(cleanup)`. Exclude from `next build` type errors by keeping test files under `src/` typed normally (they are included by `tsconfig`; add `vitest/globals` types only if `globals: true`).

## Package Legitimacy Audit

| Package | Registry | Age | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-------------|-----------|-------------|
| jsdom | npm | years | github.com/jsdom/jsdom | [OK] | Approved |
| @vitejs/plugin-react | npm | years | github.com/vitejs/vite-plugin-react | [OK] | Approved |
| @testing-library/react / jest-dom / user-event | npm | years | testing-library org | [OK] | Approved |
| vitest | npm | years, official vitest-dev/vitest | github.com/vitest-dev/vitest | [SUS] (name "close to vite" heuristic) | Approved -- false positive: vitest is the official Vite-ecosystem test runner. `` `vitest` [WARNING: slopcheck flagged as suspicious -- verify before using.] `` Planner: include a one-line `checkpoint:human-verify` or confirm via vitest.dev before install. No `postinstall` scripts on vitest, jsdom, plugin-react, RTL (npm view returned empty). |

Packages removed: none. Playwright is already pinned and installed in `test/`.

## Current State Audit (done vs missing)

| Req | Status | Evidence / what remains |
|-----|--------|-------------------------|
| OPS-03 Dockerfile | Exists. Verify only: build it, check `uv sync --frozen --no-dev` works and static copied to `/app/backend/static`. Note `COPY frontend/ ./` copies `frontend/out` excluded by `.dockerignore` (`**/out`) good |
| OPS-04 docker run | Wired (`DB_PATH=/app/db/finally.db`, `STATIC_DIR=/app/backend/static`, `CMD uvicorn`). Prove by running the exact command in success criterion 1 and `curl /api/health` |
| OPS-05 start scripts | Exist (mac `--build`, windows `-Build`, `-NoBrowser`), idempotent via `docker rm -f` first. Gaps to check: Windows script uses `docker rm -f ... *> $null` (fine) but no `$ErrorActionPreference`; mac script lacks executable bit check (`git ls-files -s scripts/*.sh` should show 100755; set with `git update-index --chmod=+x`); prints the URL; opens browser. Cannot run .ps1 from WSL except via `powershell.exe -File` (available through WSL interop; try it) |
| OPS-06 stop scripts | Exist; `docker rm -f` keeps volume. Verify `docker volume ls` still shows `finally-data` afterwards |
| OPS-07 `.env.example` | Exists with all three vars (plus `MASSIVE_POLL_INTERVAL`); `.env` gitignored. Note `load_dotenv` reads `<repo>/.env` (3 levels up from `app/main.py`); in the container that is `/app/.env` (absent) and env comes from `--env-file`, which is correct. Done; add a test/grep assertion only if cheap |
| DATA-04 persistence | Wired (volume `/app/db`, `init_db` idempotent: schema `IF NOT EXISTS`-style via executescript, seeds only when `users_profile` empty, WAL). Needs proof (see Persistence Verification). WAL caveat: after `docker rm -f` (SIGKILL) uncheckpointed WAL stays in the volume and is replayed on next open -- safe. `docker stop` first (SIGTERM, graceful) would be cleaner; consider `docker stop` then `docker rm` in stop scripts |
| UI-13 responsive | **Missing.** See Responsive Implementation |
| UI-14 testids | **6 missing:** `watchlist`, `sparkline-{T}`, `chat-toggle`, `app-header`, `position-qty-{T}`, `position-pnl-{T}` |
| TEST-04 backend route tests | Mostly there (`test_health`, `test_watchlist_api`, `test_portfolio_api`, `test_chat_api`). Audit for gaps: no `/api/stream/prices` route test file named for routes (`test_streaming_union.py`, `market/test_stream.py` exist), static mount fallthrough, 404 for unknown `/api/*` path. Add a thin `test_routes_smoke.py` only for missing status codes |
| TEST-05 frontend tests | **Missing entirely** |
| TEST-06 compose test | Exists; needs a real run |
| TEST-07 E2E scenarios | Specs 01-06 cover all 7 scenarios; verify they pass; add responsive spec (optional per UI-SPEC) and use the new testids in fresh-start (sparkline) and trading (position-qty) |

## Architecture Patterns

### Flow diagram
```
host: scripts/start_*.sh|ps1 --docker build--> image "finally"
      docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
                       |
        FastAPI :8000 -+-> /api/*  (REST, SSE)  <- SimulatorSource/MassiveSource -> PriceCache
                       +-> /*  StaticFiles(/app/backend/static = Next export)
                       +-> SQLite /app/db/finally.db  (volume finally-data)

test: docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
      finally-app (LLM_MOCK=true, tmpfs /app/db, healthcheck) <-HTTP- playwright container (BASE_URL=http://finally-app:8000)
```

### Recommended additions
```
frontend/
  vitest.config.ts, vitest.setup.ts
  src/**/__tests__/ or *.test.tsx    # colocate: lib/portfolio.test.ts, components/*.test.tsx
test/
  e2e/07-responsive.spec.ts          # viewports 1280/1024/768, scrollWidth <= innerWidth
  e2e/ or scripts: persistence check # see below
```

### Frontend test plan (TEST-05) -- keep small, one file per concern
| Concern | Target | Technique |
|---------|--------|-----------|
| Portfolio calculations | `lib/portfolio.ts` `derivePositions`, `pnlState`, `toSeries` | Pure unit tests (no DOM): totals = cash + sum(mv), P&L, ordering by market value, null portfolio, duplicate-second series |
| Formatting | `lib/format.ts` | pure |
| Price flash | `PriceCell` | render, rerender with `direction="up"` and changed `price`; assert `data-flash="up"` is set. The component sets the attr synchronously in the effect then clears it after two `requestAnimationFrame`s: assert immediately after `rerender` (before rAF) or use `vi.useFakeTimers()` + stub rAF. Also assert no flash when `live={false}` |
| Rendering with mock data | `Watchlist`/`WatchlistRow`, `PositionsTable`, `Header` | pass props directly; assert testids and text |
| Watchlist CRUD | `Watchlist` with `onAdd`/`onRemove` mocks | user-event: type ticker, click add -> `onAdd` called, error text via `watchlist-add-error`; click remove -> `onRemove`. `useWatchlist` hook: mock `global.fetch` |
| Chat rendering + loading | `ChatDock` / `ChatMessage` | mock `useChat` (`vi.mock("@/lib/useChat")`) to return `pending: true` -> `chat-loading` present, input disabled; messages with actions render `chat-action` |
| Responsive initial state | ChatDock | stub `window.matchMedia` to return `matches:false` -> `data-collapsed="true"` |

Do not unit-test lightweight-charts components (`MainChart`, `PnlChart`) in jsdom (canvas); either `vi.mock("lightweight-charts")` or skip -- E2E covers them via `pnl-chart[data-points]`.

### Responsive Implementation (UI-13, per approved UI-SPEC)
- Terminal grid: `grid-cols-[minmax(240px,30%)_1fr_48px] min-[1024px]:grid-cols-[minmax(240px,26%)_1fr_48px] min-[1280px]:grid-cols-[minmax(320px,28%)_1fr_auto]`; Tailwind 4 default breakpoints are `md`=768, `lg`=1024, `xl`=1280 (use `lg:`/`xl:`). [CITED: tailwindcss.com/docs/responsive-design]
- Bottom row: below `lg` two columns with Positions `col-span-2` on first row; at `lg+` the inherited 3 columns. Page wrapper `overflow-y-auto` below `lg`, `min-h-[240px]` on panels, `lg:overflow-hidden` + `h-full` at `lg+` to keep the no-scroll desktop layout. The current root is `flex h-full flex-col`; the tablet scroll needs the grid rows to stop being `min-h-0` constrained (use `max-lg:` variants).
- ChatDock: initial `useState(() => window.matchMedia("(min-width: 1280px)").matches)` is SSR/static-export unsafe (hydration mismatch, `window` undefined at prerender). Use `useState(false)` plus a mount `useEffect` that sets from matchMedia once (the lint rule `react-hooks/set-state-in-effect` is already disabled with a comment elsewhere in Terminal.tsx, same pattern). Overlay below 1280 when expanded: parent grid cell must be `relative` with a fixed 48px slot; the `aside` becomes `absolute inset-y-0 right-0 w-[360px] z-10` when `expanded && narrow`. Because "narrow" is also decided at mount, store a `narrow` boolean from the same matchMedia read, or use CSS only: `max-xl:absolute max-xl:inset-y-0 max-xl:right-0 max-xl:z-10` applied only when expanded -- CSS-only is simpler and resize-safe.
- Header: `hidden lg:inline` on the stale-badge text span, but keep the `stale-badge` element (E2E counts it).
- Watchlist remove button: add `max-lg:opacity-100`.
- E2E must keep existing specs unchanged: they run at 1600x1000, so desktop layout is unaffected; the dock starts **collapsed below 1280**, and the chat spec runs at 1600 (expanded). Verify `05-chat.spec.ts` still sees `chat-input` visible.

### New testids (exact placement)
| id | Where |
|----|-------|
| `watchlist` | `Watchlist.tsx` `Panel testId="watchlist"` (check the Panel call) |
| `sparkline-{T}` | `Sparkline` gets a `ticker` prop; `<svg data-testid={"sparkline-"+ticker} data-points={points.length}>` |
| `chat-toggle` | button in ChatDock (keep `aria-label` "Expand chat panel"/"Collapse chat panel" already present -- UI-SPEC says "Expand chat"; keep the existing labels, tests select by testid) |
| `app-header` | `<header>` in Header.tsx |
| `position-qty-{T}`, `position-pnl-{T}` | the quantity and unrealized P&L `<span role="gridcell">` in PositionsTable; `data-pnl` = `up|down|flat` mapped from `pnlState` (`positive|negative|flat`) |

Gotcha: positions table renders its price via `PriceCell ticker={"pos-"+ticker}` so its testid is `price-pos-AAPL`, not a collision with watchlist `price-AAPL`. Leave it.

### Persistence Verification (DATA-04, success criterion 3)
Automate as a script (`test/persistence.sh`, or documented manual step in the verification plan). Sequence using real volume semantics:
1. `docker volume rm finally-test-data`; `docker run -d --name finally-p -v finally-test-data:/app/db -p 8001:8000 -e LLM_MOCK=true finally`
2. `curl -s -X POST localhost:8001/api/portfolio/trade -H 'content-type: application/json' -d '{"ticker":"AAPL","side":"buy","quantity":2}'`; `POST /api/watchlist {"ticker":"PYPL"}`; `POST /api/chat {"message":"hello"}`
3. `docker rm -f finally-p`; start again with the same volume; assert `GET /api/portfolio` shows AAPL qty 2 and reduced cash, watchlist contains PYPL, chat history persisted (check `chat_messages` via a second chat call or sqlite read; there is no GET history endpoint in PLAN.md, so read via `docker exec ... python -c "sqlite3..."` or accept that the chat table survives because the file does).
Use a different container name, port and volume from the user's `finally` so the check never touches real data.
Windows/WSL: run from a cwd under /mnt/c (docker wrapper requirement).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Frontend test runner/DOM matchers | custom harness | Vitest + RTL + jest-dom |
| Waiting for E2E state | `sleep`/fixed timeouts | Playwright `expect.poll` / auto-waiting `expect` (already the pattern in helpers) |
| Container readiness | sleep loops | compose `healthcheck` + `depends_on: condition: service_healthy` (already present) |
| Breakpoint logic in JS | resize listeners | Tailwind `max-lg:`/`xl:` variants, one `matchMedia` read at most |
| Idempotent container restart | state checks | `docker rm -f` before `docker run` (already used) |

## Common Pitfalls

1. **Flaky backend test.** `tests/market/test_source.py::test_cache_seeded_before_start_returns` failed once in the full run (assertion at line 25: every price within 1% of seed) and passes in isolation (5 passed). The fixture starts the simulator with a 20ms interval, so ticks plus random "events" (2-5% jumps) occur before the assertion; it is a test-design flake, not a product bug. Fix: assert on the cache immediately after `start` without the running loop, or use a long interval / seeded RNG; do not loosen tolerance blindly. Root cause should be proven by repeating the single test ~50x (`uv run pytest tests/market/test_source.py -k seeded --count`/loop) before fixing. [VERIFIED: ran full suite: 1 failed, 166 passed in 38s; isolated: pass]
2. **SSR/prerender with `window`/`matchMedia`.** Static export prerenders client components; reading `window` in a `useState` initializer breaks the build or hydrates mismatched. Read it in an effect.
3. **jsdom lacks `ResizeObserver`, `matchMedia`, canvas.** `useSize` and charts need stubs/mocks in `vitest.setup.ts`.
4. **E2E tests share one app state** (single user, serial). The compose stack uses `tmpfs` DB so each run is fresh, but within a run order matters (`01-fresh-start` expects $10,000 cash and runs first). New specs must be numbered after the existing ones and not mutate defaults before spec 01 (e.g. `07-responsive` is read-only; persistence runs separately, not in the Playwright suite).
5. **`docker compose ... up` exit code.** Must use `--abort-on-container-exit --exit-code-from playwright` (documented in `test/README.md`) or failures return 0. `npm install` runs inside the Playwright container every run (slow but offline-unsafe); `volumes: - /work/node_modules` anonymous volume is intentional so host `node_modules` (Windows binaries) don't leak in.
6. **Windows host node_modules in test/** (`test/node_modules` exists from Windows): do not bind-mount them into Linux container (already guarded by the anonymous volume). `.dockerignore` excludes `test`.
7. **Docker build on Node 20 with vitest 5.** EBADENGINE warnings during `npm ci`; harmless. Do not set `engine-strict`.
8. **`next build` type-checks test files** (tsconfig includes everything). Test imports must type-check under `next build`; if friction, add `"exclude": ["**/*.test.ts*", "vitest.*"]` to `frontend/tsconfig.json` -- but then `npm run typecheck` skips tests; prefer a separate `tsconfig` only if needed.
9. **Script execute bit on Windows checkout.** `.sh` files created on /mnt/c may be 0755 in WSL but git may record 100644; check `git ls-files -s scripts`.
10. **Responsive overlay must not reflow panels:** the dock slot stays 48px; do not put the absolutely positioned aside outside a `relative` ancestor.
11. **Port/name collisions:** start script uses fixed container name `finally` and port 8000; a stale n8n/other service on 8000 would fail `docker run`. Not a code issue; surface the docker error (script has `set -e`).

## Code Examples

```ts
// vitest.config.ts  (Source: vitest.dev config docs; plugin-react README)
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: { environment: "jsdom", setupFiles: ["./vitest.setup.ts"], globals: true },
});
```
```ts
// vitest.setup.ts
import "@testing-library/jest-dom/vitest";
class RO { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver ??= RO as unknown as typeof ResizeObserver;
window.matchMedia ??= ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, onchange: null, dispatchEvent: () => false })) as typeof window.matchMedia;
```
```ts
// test/e2e/07-responsive.spec.ts
import { expect, test } from "@playwright/test";
import { openApp } from "./helpers";

for (const width of [1280, 1024, 768]) {
  test(`no horizontal scroll at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await openApp(page);
    for (const id of ["app-header", "watchlist", "chat-panel", "main-chart"]) await expect(page.getByTestId(id)).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
```
Note `openApp` expects connected status; at narrow widths it still works since dock state is irrelevant. Assert `chat-panel[data-collapsed=true]` at 1024/768 and expanding via `chat-toggle` keeps `scrollWidth <= innerWidth`.

## State of the Art
| Old | Current | Impact |
|-----|---------|--------|
| Jest + babel for React | Vitest (Vite-native) | Faster, ESM, no Next/jest config needed for pure client code |
| `docker-compose` v1 binary | `docker compose` v2+ plugin (v5.5.1 here) | Use `docker compose` (already in README) |
| Tailwind 3 `screens` config | Tailwind 4 CSS-first `@theme`, default breakpoints built in | `max-lg:`/`xl:` variants work without config |

## Assumptions Log
| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vitest 5 + plugin-react 6 + vite 8 combine cleanly with Next 16.4 and TS 5.9 without extra config | Standard Stack | Install friction; fall back to vitest 4.1.x + plugin-react 5 + vite 7 |
| A2 | `powershell.exe` is callable from WSL to smoke-test the `.ps1` scripts | Audit | Windows scripts verified by inspection only |
| A3 | Flaky test cause is the 20ms loop + random events (inferred from code, not yet reproduced N times) | Pitfalls | Wrong fix; reproduce first per user rule |
| A4 | `docker stop` before `rm` is preferable for graceful WAL checkpoint | Audit | None functionally; `rm -f` already safe |

## Open Questions
1. **Chat history on restart has no read endpoint.** PLAN.md defines only `POST /api/chat`; does the UI show prior messages after reload? Check `useChat.ts` -- if history is not loaded on mount, success criterion 3 ("chat history still there") is only satisfied at the DB level. Recommendation: confirm in `frontend/src/lib/useChat.ts`/`backend/app/chat/router.py`; if absent, add a minimal `GET /api/chat/history` is scope creep -- prefer verifying DB-level persistence and flag to user.
2. **Tablet "cannot be proven in jsdom".** Layout checks must be Playwright-only (scrollWidth assertions).

## Environment Availability
| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker engine | OPS-03/04, TEST-06 | yes | 29.8.1 | — |
| Docker Compose | TEST-06 | yes | v5.5.1 | — |
| Playwright image | TEST-06/07 | yes (pulled) | v1.64.1-noble | — |
| `finally` image / volume | OPS-04 | yes (built earlier; rebuild needed after changes) | — | `--build` |
| Node (Windows wrapper) | frontend tests | yes | v24.21.0 | — |
| uv / Python 3.14 | backend tests | yes | tests ran | — |
| `.env` | docker run | yes (real keys, gitignored) | — | start script copies `.env.example` |
| powershell.exe | smoke .ps1 | unverified | — | inspect only |

All shell/docker/npm commands must run with cwd under `/mnt/c` (wrapper requirement).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend | pytest 9.1.1 + pytest-asyncio (auto mode), config in `backend/pyproject.toml` |
| Frontend | Vitest 5.0.5 + RTL (Wave 0: install) |
| E2E | Playwright 1.64.1, `test/playwright.config.ts`, serial, workers 1 |
| Quick run | backend: `cd backend && uv run pytest -q -x` (~40s full); frontend: `cd frontend && npm test` |
| Full suite | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` then `down -v` |

### Phase Requirements -> Test Map
| Req | Behavior | Type | Command | Exists? |
|-----|----------|------|---------|---------|
| OPS-03/04 | image builds; container healthy on :8000 | smoke | `docker build -t finally . && docker run ... && curl /api/health` | script Wave 0 |
| OPS-05/06 | start builds/runs/prints URL; stop removes container, keeps volume; repeat-safe | smoke | run each script twice; `docker ps`, `docker volume ls` | manual-ish script |
| OPS-07 | `.env.example` has 3 vars; `.env` ignored | static | `grep` + `git check-ignore .env` | trivial |
| DATA-04 | state survives rm + re-run on same volume | integration | `test/persistence.sh` | Wave 0 |
| UI-13 | no horizontal scroll 768-1280; dock collapsed <1280 | e2e | Playwright `07-responsive.spec.ts` | Wave 0 |
| UI-14 | 6 new hooks present with data attrs | unit + e2e | vitest component tests + specs 01/03 | Wave 0 |
| TEST-04 | routes: status codes, shapes, errors | integration | `uv run pytest tests -k api` | exists, audit gaps |
| TEST-05 | portfolio calc, flash, watchlist CRUD, chat loading | unit | `npm test` | Wave 0 |
| TEST-06 | compose runs app + playwright with LLM_MOCK | e2e infra | compose command above | exists, run it |
| TEST-07 | 7 scenarios pass | e2e | same | specs 01-06 exist |

### Sampling Rate
- Per task commit: relevant quick command (pytest `-x` for backend work; `npm test` + `npm run typecheck && npm run lint` for frontend).
- Per wave merge: backend full + frontend full + `npm run build`.
- Phase gate: full compose E2E green + persistence script green + start/stop scripts run twice.

### Wave 0 Gaps
- [ ] Install vitest toolchain; `vitest.config.ts`, `vitest.setup.ts`, `test` script in `frontend/package.json`
- [ ] `frontend/src/**/*.test.ts(x)` files per concern table
- [ ] `test/e2e/07-responsive.spec.ts`
- [ ] `test/persistence.sh`
- [ ] Fix flaky `test_cache_seeded_before_start_returns`

## Security Domain
`security_enforcement` not set in config (treated as enabled). Single-user local app; no auth by design.

| ASVS | Applies | Control |
|------|---------|---------|
| V2/V3/V4 | no | Single user, no login (PLAN.md) |
| V5 Input validation | yes (existing) | pydantic/FastAPI validation, 422 handler; tests assert 422 |
| V6 Crypto | no | — |
| V14 Config/deploy | yes | `.env` gitignored and in `.dockerignore` (never baked into image); `--env-file` at run; do not `COPY .env`; `ghcr.io/astral-sh/uv:latest` unpinned (supply chain: consider pinning a version tag) |

| Threat | Mitigation |
|--------|-----------|
| Secrets in image layers | `.dockerignore` has `.env`; verify with `docker run --rm finally ls -a /app` |
| API keys in logs/tests | tests use `LLM_MOCK=true`; compose test sets `MASSIVE_API_KEY: ""` |
| Container runs as root | acceptable for a local course app; note only |

## Project Constraints (from CLAUDE.md)
- `uv run` / `uv add` only; never `python3`/`pip`. Latest APIs. No emojis in code/logs.
- Simple, incremental, no over-engineering, no defensive programming; short modules/functions, concise docstrings.
- Root cause with evidence before any fix (applies to the flaky test).
- Dark theme colors fixed; E2E with `LLM_MOCK=true`. README concise.
- Work through a GSD command before editing files.

## Sources
### Primary
- Codebase audit: Dockerfile, docker-compose.yml, .dockerignore, .gitignore, .env.example, scripts/*, test/*, backend/app/{main,db}.py, frontend components/lib, 06-UI-SPEC.md, REQUIREMENTS.md, ROADMAP.md, PLAN.md
- `uv run pytest` full run (166 pass / 1 flaky); `docker`/`docker compose` version and `docker images/volume ls`
- npm registry (`npm view`) for vitest, vite, jsdom, plugin-react, RTL packages (versions, engines, peers)
### Secondary
- slopcheck scan results (above); Tailwind v4 responsive docs and Vitest docs from training knowledge, not re-fetched this session [ASSUMED] (A1)

## Metadata
**Confidence:** Standard stack MEDIUM (versions verified on registry, toolchain not exercised); architecture/audit HIGH (read from code); pitfalls MEDIUM-HIGH.
**Research date:** 2026-10-20 -- valid ~30 days.
