# Phase 1: Live Price Terminal - Research

**Researched:** 2026-10-19
**Domain:** FastAPI SSE + GBM market simulator (numpy) + Next.js 16.4 static export + Tailwind 4.3 terminal UI
**Confidence:** HIGH (versions, SSE API, static serving, shutdown, dev proxy, lint/typecheck were all verified by running them in a scratch project in this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Market data engine**
- Follow the prior design docs `planning/MARKET_INTERFACE.md` and `planning/MARKET_SIMULATOR.md`: abstract `MarketDataSource` (start / stop / add_ticker / remove_ticker / get_tickers); `PriceCache` as the single source of truth with a version counter for SSE change detection
- Correlated moves via Cholesky decomposition of a sector correlation matrix (tech 0.6, finance 0.5, cross-sector 0.3), using numpy
- Random shock events: ~0.1% chance per tick per ticker of a sudden 2-5% move
- Tickers are the 10 PLAN.md defaults, hardcoded until Phase 2 adds SQLite; realistic seed prices (AAPL ~$190, GOOGL ~$175, etc.) and per-ticker drift/volatility

**Stream contract**
- `GET /api/stream/prices`: one SSE message per ~500ms tick whose data is a JSON map keyed by ticker; each value has `ticker, price, previous_price, timestamp, direction, day_change_pct`
- Daily change % is computed by the backend against the session-open price (seed price for the simulator)
- Server sends `retry: 1000`; client uses native EventSource retry. Connection dot: `connected` on open, `reconnecting` on error while EventSource retries, `disconnected` when closed
- `GET /api/health` returns exactly `{"status": "ok"}` (E2E `01-fresh-start.spec.ts` asserts this)

**Frontend foundation**
- Next.js 16.4 App Router, React 19.3, TypeScript, `output: 'export'`, Tailwind 4.3 with theme tokens in CSS (PLAN.md colors: bg `#0d1117`/`#1a1a2e`, accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991`; no pure black)
- Sparklines: small inline SVG component, capped buffer (~120 points) accumulated from SSE since page load. Lightweight Charts 5.2 is reserved for the main chart and P&L chart in later phases
- Build the final terminal grid shell now (header, watchlist, main chart area, chat dock); only the header connection dot and the watchlist are live, the rest are labeled placeholders
- Use the E2E test ids from day one: `connection-status` with `data-status` (`connected` / `reconnecting` / `disconnected`), `watchlist-row-{TICKER}`, `price-{TICKER}`
- Price flash: apply a green/red background class on change and fade over ~500ms via CSS transition

**Project layout and dev loop**
- `backend/` is a uv project with an `app/` package: `main.py`, `market/`, `api/`. FastAPI mounts the static export from `STATIC_DIR` (default `backend/static`) after the API routes
- Dev loop: `npm run build` produces `frontend/out`, which is copied or pointed to as the static dir so FastAPI serves everything from one origin; `next dev` rewrites `/api/*` to `http://localhost:8000` for fast UI iteration
- Python deps via `uv add`: fastapi, uvicorn[standard], numpy; dev: pytest, pytest-asyncio, httpx
- Tests in this phase: backend pytest for market data (TEST-01). Frontend tests come with TEST-05 in Phase 6

### Claude's Discretion
- Exact module split inside `app/market/`, the SSE implementation (StreamingResponse vs sse library), and component structure inside `frontend/src/`

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope. (Not in this phase: SQLite and watchlist editing = Phase 2, trading/portfolio numbers = Phase 3, chat = Phase 4, Massive = Phase 5, Docker and E2E = Phase 6.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MKT-01 | One abstract market-data interface | `MarketDataSource` ABC + `create_market_data_source` factory (Phase 1 factory only returns simulator); conformance test |
| MKT-02 | GBM with per-ticker drift/vol, ~500ms | Section "Simulator" formulas; `dt = 0.5 / (252*6.5*3600)`; asyncio loop with `sleep(0.5)` |
| MKT-03 | Correlated moves | Cholesky of sector matrix; verified PD (min eigenvalue 0.4) and realised correlations 0.60 / 0.50 / 0.30 |
| MKT-04 | Sudden 2-5% move | `event_probability=0.001`; test with probability 1.0 |
| MKT-05 | Realistic seed prices | `SEED_PRICES` table from `MARKET_SIMULATOR.md` |
| MKT-08 | Single writer to in-memory cache (latest, previous, timestamp) | `PriceCache` with lock, `version`, session-open for `day_change_pct` |
| STRM-01 | SSE consumable by native EventSource | `fastapi.sse.EventSourceResponse` (FastAPI 0.146.0), verified with curl |
| STRM-02 | All tickers at ~500ms | Per-connection loop, send when `cache.version` changed, first send immediate |
| STRM-03 | ticker, price, previous, timestamp, direction | Payload map; plus `day_change_pct` |
| STRM-04 | Auto reconnect | `retry: 1000` on first event; native EventSource; connection-state mapping |
| OPS-01 | One origin, API + static | `app.mount("/", StaticFiles(..., html=True))` registered last; verified |
| OPS-02 | Health | `GET /api/health` -> `{"status": "ok"}` |
| UI-01 | Next.js TS static export, Tailwind dark theme | Verified `output: 'export'` build + `@theme` tokens compiled to CSS |
| UI-03 | Watchlist with symbol, price, day %, sparkline | Hook + inline SVG polyline pattern |
| UI-04 | Flash green/red, ~500ms fade | `data-flash` attribute + double rAF + CSS transition; lint-verified |
| TEST-01 | pytest covers market data | Validation Architecture section (Massive parsing portion is Phase 5, see note) |
</phase_requirements>

## Summary

Everything the phase needs is available in current, stable releases and the whole stack was exercised end to end in a scratch project: Next 16.4.2 static export with Tailwind 4.3.3, FastAPI 0.146.0 serving an SSE route plus the export from one origin, numpy 2.5.4 Cholesky correlation, and pytest-asyncio 1.4.0. FastAPI now ships native SSE (`fastapi.sse.EventSourceResponse` + `ServerSentEvent`, added in 0.135.0). Use it instead of a third-party SSE library or hand-built `StreamingResponse`. It sets `Cache-Control: no-cache`, `X-Accel-Buffering: no`, and a 15 s keep-alive comment automatically, and a yielded `dict` is JSON-encoded into `data:`.

Three non-obvious findings drive the plan. (1) **uvicorn hangs on shutdown with an open SSE connection** ("Waiting for connections to close" forever); the fix is `--timeout-graceful-shutdown 2`, which cancels the stream task after 2 s (it logs a harmless `CancelledError` traceback). The Dockerfile CMD does not have this flag yet. (2) **TypeScript 7.0.2 is `latest` on npm but breaks `eslint-config-next` 16.4.2** (`typescript-eslint does not support TS 7.0`); pin `typescript@~5.9`. (3) **`next dev` applies `rewrites` even with `output: 'export'` but both `next dev` and `next build` print a warning**; use a phase-aware `next.config.ts` (rewrites only in dev, `output: 'export'` only for build) to get a clean build and a proxy that streams SSE without buffering (verified).

Environment hazards for the plan: a Docker container named `finally` (old image) is currently running and owns port 8000 on the host, so verification must use another port (for example 8010) or the executor must `docker stop finally` first. Environment variables set in WSL do not reach the Windows-native `node`/`npm` wrappers unless listed in `WSLENV`.

**Primary recommendation:** Build the backend first (market package + pytest + `/api/health` + SSE route + static mount, verified by curl on port 8010), then the frontend shell (hook, cells, sparkline, grid), then wire static serving (`STATIC_DIR=../frontend/out`) and run the curl/grep smoke checks. Keep modules short and avoid defensive code, per CLAUDE.md.

## Project Constraints (from CLAUDE.md)

- Simple, incremental steps; validate each increment. Do not over-engineer; no defensive programming; use exception handling only where needed.
- Use latest library APIs.
- Python: `uv` only. `uv run xxx`, `uv add xxx`; never `python3`/`pip` (this research used `uv run` for all Python).
- Identify root cause with evidence before fixing; no workarounds.
- Concise docstrings; sparing comments outside docstrings. Short modules, short functions, clear names.
- No emojis in code, print statements or logging.
- Keep README.md concise.
- `.gitignore` has a Python `lib/` rule; `!frontend/src/lib/` negation already added (verify it stays and that `frontend/src/lib` files show up in `git status`).
- Backend pins Python 3.14. Environment is WSL2 on `/mnt/c`; `node`/`npm`/`npx`/`docker` are Windows wrappers and must run with cwd under `/mnt/c`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| GBM price generation, correlation, shocks | API / Backend (in-process task) | - | PLAN.md: in-process simulator, no external dependency |
| Latest-price store, session-open, version | API / Backend (`PriceCache`) | - | Single source of truth for SSE and later portfolio/trades |
| `day_change_pct`, `direction` computation | API / Backend | - | Locked: backend computes; client never recomputes |
| SSE push at ~500ms | API / Backend | Browser (EventSource) | One-way push; browser owns reconnect |
| Connection status state machine | Browser / Client | - | Derived from EventSource events |
| Sparkline buffer (120 pts) | Browser / Client | - | "Accumulated since page load" is a client concern |
| Price flash animation | Browser / Client (CSS transition) | - | Pure presentation |
| Serving the UI | API / Backend (`StaticFiles`) | CDN / Static (Next export) | One origin, one container |
| Dev-time `/api` proxy | Frontend dev server (`next dev` rewrites) | - | Dev only; absent from the export |
| Health check | API / Backend | - | OPS-02 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.146.0 | API, SSE (`fastapi.sse`), lifespan, static mount | Locked stack; native SSE since 0.135.0 [VERIFIED: PyPI + fastapi.tiangolo.com/tutorial/server-sent-events] |
| uvicorn[standard] | 0.54.0 | ASGI server | Locked; `--timeout-graceful-shutdown` verified [VERIFIED: PyPI + run] |
| numpy | 2.5.4 | Cholesky, standard normals | Locked [VERIFIED: PyPI + run] |
| next | 16.4.2 | App Router, static export | Locked [VERIFIED: npm registry] |
| react / react-dom | 19.3.1 | UI | Locked [VERIFIED: npm registry] |
| tailwindcss + @tailwindcss/postcss | 4.3.3 | Styling, `@theme` tokens | Locked; `@import "tailwindcss"` + postcss plugin [CITED: tailwindcss.com/docs/installation/framework-guides/nextjs] |
| postcss | 8.5.31 | Required by the Tailwind plugin | [VERIFIED: npm registry] |
| typescript | **~5.9.3 (pin)** | Types | TS 7.0.2 breaks eslint-config-next (see Pitfall 2) [VERIFIED: ran eslint with both] |

### Supporting (dev)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | Backend tests | TEST-01 [VERIFIED: PyPI] |
| pytest-asyncio | 1.4.0 | Async tests for the data source | `asyncio_mode = "auto"` [VERIFIED: PyPI; CITED: pytest-asyncio.readthedocs.io] |
| httpx | 0.28.1 | Route tests (`/api/health`) | Locked in CONTEXT [VERIFIED: PyPI] |
| eslint | 10.13.0 | Lint | `npm run lint` [VERIFIED: ran] |
| eslint-config-next | 16.4.2 | Next + React hooks rules | flat config via `eslint-config-next/core-web-vitals` and `/typescript` [VERIFIED: ran] |
| @types/react 19.3.0, @types/node 26.6.5 | - | Types | [VERIFIED: npm registry] |

Not used this phase: `lightweight-charts` 5.2.1 (Phase 2+). No SSE helper library, no shadcn, no icon library.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fastapi.sse.EventSourceResponse` | `sse-starlette` / hand-rolled `StreamingResponse` | Native is built in, tested here, no extra dependency; do not add alternatives |
| Phase-aware `next.config.ts` | Unconditional `output: 'export'` + `rewrites()` | Works in dev but prints a "will not work with output: export" warning on every build and dev start |

**Installation:**
```bash
# backend (from repo root)
mkdir backend && cd backend
uv init --bare --python 3.14 .          # pyproject.toml with no build-system: virtual project
uv add fastapi "uvicorn[standard]" numpy
uv add --dev pytest pytest-asyncio httpx

# frontend (cwd must be under /mnt/c)
mkdir frontend && cd frontend
npm init -y   # then set scripts/private; or write package.json by hand
npm install next@16.4.2 react@19.3.1 react-dom@19.3.1 tailwindcss @tailwindcss/postcss postcss
npm install -D typescript@~5.9 @types/react @types/node eslint eslint-config-next@16.4.2
```
`package.json` scripts: `"dev": "next dev"`, `"build": "next build"`, `"lint": "eslint"`, `"typecheck": "tsc --noEmit"`. (`next lint` is not used; plain `eslint` works with the flat config below.)

**Version verification:** `npm view` and PyPI JSON were queried today (2026-10-19); the versions above are the registry `latest`, except TypeScript which is deliberately pinned.

## Package Legitimacy Audit

slopcheck is not installed in this environment (and CLAUDE.md forbids `pip install`); it was not run. Every package below is named in the official docs of the locked stack (FastAPI, Next.js, Tailwind, pytest-asyncio docs, CONTEXT.md) and resolved on the correct registry, so they are tagged `[CITED]`, not `[ASSUMED]`. The planner does not need per-package human-verify gates for these. `npm install` of the eslint chain printed one transitive postinstall (`unrs-resolver` via eslint-config-next, standard for the import resolver); no direct dependency has a suspicious postinstall.

| Package | Registry | Age | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-------------|-----------|-------------|
| fastapi, uvicorn, numpy, pytest, pytest-asyncio, httpx | PyPI | many years | well-known | not run | Approved (official/locked) |
| next, react, react-dom, tailwindcss, @tailwindcss/postcss, postcss, typescript, eslint, eslint-config-next, @types/* | npm | many years | well-known | not run | Approved (official/locked) |

**Packages removed due to slopcheck [SLOP] verdict:** none (not run)
**Packages flagged [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                      lifespan startup
                           |
                           v
 SimulatorDataSource.start(DEFAULT_TICKERS)
   |  seeds PriceCache (seed price = session open)
   |  asyncio.create_task(_run_loop)
   v
 _run_loop: every 0.5 s
   GBMSimulator.step()  --(z -> L@z correlated, GBM, rare 2-5% shock)-->  {ticker: price}
   |
   v
 PriceCache.update(ticker, price)   (previous_price, direction, day_change_pct, version += 1)
   |
   | read (never calls the source)
   v
 GET /api/stream/prices  (EventSourceResponse, async generator per connection)
   loop: if cache.version != last_version -> yield ServerSentEvent(data={TICKER: quote,...}); sleep 0.5
   first event also carries retry=1000
   |
   v   text/event-stream, one origin :8000
 Browser EventSource  --onopen/onerror/onmessage-->  usePriceStream()
   |                                   |
   | status                            | one setState per message
   v                                   v
 Header dot (connection-status)   Watchlist rows: PriceCell (flash), Day %, Sparkline (120-pt buffer)

 Browser GET /            -> FastAPI StaticFiles(html=True) mounted LAST at "/" -> out/index.html
 Browser GET /api/health  -> {"status": "ok"}
 Dev: next dev :3000  --rewrites /api/:path* -->  uvicorn :8000
```

### Recommended Project Structure
```
backend/
├── pyproject.toml            # requires-python >=3.14; [tool.pytest.ini_options] asyncio_mode = "auto"
├── uv.lock
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, lifespan, include routers, mount static LAST
│   ├── market/
│   │   ├── __init__.py       # public exports
│   │   ├── models.py         # PriceUpdate (frozen dataclass)
│   │   ├── cache.py          # PriceCache
│   │   ├── interface.py      # MarketDataSource ABC
│   │   ├── seed_prices.py    # SEED_PRICES, TICKER_PARAMS, groups, correlations
│   │   ├── simulator.py      # GBMSimulator (pure) 
│   │   ├── simulator_source.py  # SimulatorDataSource (asyncio adapter)
│   │   └── factory.py        # create_market_data_source (Phase 1: simulator only)
│   └── api/
│       ├── health.py         # GET /api/health
│       └── stream.py         # GET /api/stream/prices
└── tests/market/             # test_simulator.py, test_cache.py, test_source.py, test_stream.py
frontend/
├── package.json  next.config.ts  postcss.config.mjs  eslint.config.mjs  tsconfig.json
└── src/
    ├── app/ (layout.tsx, page.tsx, globals.css)
    ├── components/ (Header, ConnectionDot, Watchlist, WatchlistRow, PriceCell, Sparkline, Panel, ChatDock)
    └── lib/ (usePriceStream.ts, format.ts)   # not ignored thanks to !frontend/src/lib/
```
`app/` router directory may sit under `src/app` (Next supports `src/`); set `tsconfig` `include` accordingly (Next rewrites tsconfig on first build and adds `.next/dev/types/**/*.ts`; commit that result). Add `next-env.d.ts` to `.gitignore` (generated).

### Pattern 1: Native SSE route (verified)
```python
# backend/app/api/stream.py
# Source: fastapi.tiangolo.com/tutorial/server-sent-events + run in this session
import asyncio
from collections.abc import AsyncIterable
from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent
from app.market import PriceCache

def create_stream_router(cache: PriceCache, interval: float = 0.5) -> APIRouter:
    router = APIRouter()

    @router.get("/api/stream/prices", response_class=EventSourceResponse)
    async def stream_prices() -> AsyncIterable[ServerSentEvent]:
        last_version, retry = -1, 1000
        while True:
            if cache.version != last_version:
                last_version = cache.version
                payload = {t: u.to_dict() for t, u in cache.get_all().items()}
                yield ServerSentEvent(data=payload, retry=retry)   # retry sent once is enough
                retry = None
            await asyncio.sleep(interval)

    return router
```
Observed wire format (curl): `content-type: text/event-stream; charset=utf-8`, `cache-control: no-cache`, `x-accel-buffering: no`, chunked; first event is `data: {...}` then `retry: 1000` lines in the same event; subsequent events every ~500 ms. `ServerSentEvent.data` is always JSON-encoded; `retry` is milliseconds. `last_version = -1` per connection means a new client gets a snapshot immediately even if prices have not changed.

Do not wrap the loop in `try/except CancelledError`; the cancellation on client disconnect is handled by the framework.

### Pattern 2: Serve the export after API routes (verified)
```python
# backend/app/main.py
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).parent.parent / "static"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await source.start(DEFAULT_TICKERS)
    yield
    await source.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(health_router)
app.include_router(create_stream_router(cache))
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True, check_dir=False), name="static")
```
Verified: `/` -> 200 `text/html`, `/_next/static/chunks/*.css` -> 200, unknown path -> 404, `/api/nope` -> 404 (falls to the static mount). `StaticFiles` raises `RuntimeError: Directory '...' does not exist` at import unless `check_dir=False`, which would break `uv run pytest` when no export has been built yet; so use `check_dir=False`. The app is a single page (`/` only), so no client-side route fallback is needed.

### Pattern 3: Phase-aware `next.config.ts` (verified)
```ts
// frontend/next.config.ts
import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

export default function config(phase: string): NextConfig {
  if (phase === PHASE_DEVELOPMENT_SERVER) {
    return { async rewrites() { return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }]; } };
  }
  return { output: "export" };
}
```
Verified: `next build` -> clean (no rewrites warning), `out/index.html`, `out/_next/static/chunks/*.css` containing `--color-bg:#0d1117`. Docs list Rewrites as unsupported with static export [CITED: nextjs.org/docs/app/guides/static-exports]; with the naive unconditional config, both `next build` and `next dev` print a warning (observed) but dev rewriting still works. Through the dev rewrite proxy, SSE events arrived every ~500 ms (not buffered) and there was no `content-encoding` header on `text/event-stream`, so `compress: false` is not needed. Use `npm run build` for the real verification of the export, `next dev` only for UI iteration.

### Pattern 4: Tailwind 4.3 in Next 16
`postcss.config.mjs`: `export default { plugins: { "@tailwindcss/postcss": {} } };` (ESLint warns about anonymous default export; assign to `const config` first). `globals.css`: `@import "tailwindcss";` then `@theme { --color-bg: #0d1117; --color-surface: #161b22; --color-border: #30363d; --color-up: #3fb950; --color-down: #f85149; --color-warn: #d29922; --color-accent: #ecad0a; --color-primary: #209dd7; --color-submit: #753991; --color-text: #e6edf3; --color-muted: #8b949e; }`. Utility classes derive from tokens (`bg-bg`, `text-up`, `border-border`) and the theme variables are also usable as `var(--color-up)` in plain CSS (flash/transition rules). Verified that `@theme` tokens compile into the emitted CSS and utilities appear in the exported HTML. No `tailwind.config.js` is needed. Colour names `text`/`muted` are legal; use `text-muted` per UI-SPEC naming (`--color-text-muted` in UI-SPEC: define `--color-text-muted` to match the spec literally).

### Pattern 5: Stream hook, no setState-in-effect (lint-verified)
```tsx
// frontend/src/lib/usePriceStream.ts
"use client";
import { useEffect, useState } from "react";
export type Quote = { ticker: string; price: number; previous_price: number; timestamp: number; direction: "up" | "down" | "flat"; day_change_pct: number };
export type Status = "connected" | "reconnecting" | "disconnected";
const MAX_POINTS = 120;

export function usePriceStream() {
  const [status, setStatus] = useState<Status>("reconnecting");   // initial "Connecting" state per UI-SPEC
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [history, setHistory] = useState<Record<string, number[]>>({});
  useEffect(() => {
    const es = new EventSource("/api/stream/prices");
    es.onopen = () => setStatus("connected");
    es.onerror = () => setStatus(es.readyState === EventSource.CLOSED ? "disconnected" : "reconnecting");
    es.onmessage = (e) => {
      const next: Record<string, Quote> = JSON.parse(e.data);
      setQuotes(next);
      setHistory((prev) => Object.fromEntries(Object.entries(next).map(([t, q]) => [t, [...(prev[t] ?? []), q.price].slice(-MAX_POINTS)])));
    };
    return () => es.close();
  }, []);
  return { status, quotes, history };
}
```
Same `"use client"` hook + `PriceCell` below pass `eslint` (config below) and `tsc --noEmit` with eslint-config-next 16.4.2 (its react-hooks rules flag `setState` called synchronously inside an effect body; all setState calls above are inside event handlers, so they are fine).

### Pattern 6: Flash on the price cell
```tsx
export function PriceCell({ ticker, price, direction }: { ticker: string; price?: number; direction?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || (direction !== "up" && direction !== "down")) return;
    el.removeAttribute("data-flash");
    void el.offsetWidth;                 // restart the flash on rapid consecutive ticks
    el.dataset.flash = direction;
    let id2 = 0;
    const id1 = requestAnimationFrame(() => { id2 = requestAnimationFrame(() => el.removeAttribute("data-flash")); });
    return () => { cancelAnimationFrame(id1); cancelAnimationFrame(id2); };
  }, [price, direction]);
  return <span ref={ref} data-testid={`price-${ticker}`} className="price-cell">{price === undefined ? "--" : `$${price.toFixed(2)}`}</span>;
}
```
CSS (plain, in `globals.css`): `.price-cell { transition: background-color 500ms ease-out; } .price-cell[data-flash="up"] { background-color: rgba(63,185,80,.30); transition: none; } .price-cell[data-flash="down"] { background-color: rgba(248,81,73,.30); transition: none; } @media (prefers-reduced-motion: reduce) { .price-cell { transition-duration: 150ms; } }`. The `price-{TICKER}` element must contain only the formatted price (E2E `readNumber`). Stop flashing while status is not `connected` (pass `direction={undefined}`), and show muted text per UI-SPEC. `toLocaleString("en-US", {minimumFractionDigits: 2})` for thousands separators (`$1,234.56`).

### Pattern 7: Sparkline (pure SVG)
`points` = map of buffer to `x = i * 64 / (n-1)`, `y = 18 - (p - min) / (max - min || 1) * 16` (so range 2..18; flat series -> y = 10). Render nothing when `n < 2`. `<polyline fill="none" stroke-width="1.5" vector-effect="non-scaling-stroke" points=... />`, `aria-hidden`. Stroke is `var(--color-up)` or `var(--color-down)` from `day_change_pct >= 0`.

### Pattern 8: Simulator essentials (verified math)
- `dt = 0.5 / (252 * 6.5 * 3600)`; `price *= exp((mu - sigma**2/2) * dt + sigma * sqrt(dt) * Z)`, `Z = L @ standard_normal(n)`.
- Correlation matrix rule: TSLA with anything 0.3; both tech 0.6; both finance 0.5; otherwise 0.3. Verified with numpy 2.5.4: matrix is positive definite (min eigenvalue 0.40), 200k-sample realised correlations AAPL-GOOGL 0.599, JPM-V 0.498, AAPL-JPM 0.297, TSLA-AAPL 0.299.
- Keep full-precision prices in the engine; round to 2 dp only when emitting/caching.
- Shock: `if random.random() < 0.001: price *= 1 + random.uniform(0.02, 0.05) * random.choice([-1, 1])`.
- Seed prices/params exactly as the table in `planning/MARKET_SIMULATOR.md` section 5.
- Use `numpy.random.default_rng()` instance (injectable seed) rather than the global `np.random.seed`; makes tests deterministic without global state. `random` module for shocks can use a `random.Random(seed)` instance too.
- `PriceCache`: `update(ticker, price, timestamp=None)` computes `previous_price` from the existing entry, records `session_open` on first update for that ticker, bumps `version`, uses `threading.Lock`. `PriceUpdate.to_dict()` returns `ticker, price, previous_price, timestamp, direction, day_change_pct` (round `day_change_pct` to 2 dp; `(price - open) / open * 100`). The prior design's `change` / `change_percent` fields are not in the locked contract; either drop them or keep them as extras, but `day_change_pct` is required.
- `MarketDataSource` ABC exactly as in `planning/MARKET_INTERFACE.md` section 2.3; `start()` seeds the cache before returning so the first SSE event has data; `stop()` cancels the task and awaits it, idempotent.

### Anti-Patterns to Avoid
- **Re-sorting watchlist rows on price change:** order is fixed per UI-SPEC.
- **Client recomputing `day_change_pct`:** locked to backend.
- **`output: 'export'` plus unconditional `rewrites`:** warnings on every build; use the phase-aware config.
- **Calling `source.get_price()` from the SSE route:** read only the cache.
- **A `try/except Exception` around the whole SSE loop, or defensive input checks everywhere:** CLAUDE.md says no defensive programming. One `logger.exception` guard around `sim.step()` in the simulator loop is the single justified exception (a stray error must not kill the price stream).
- **Cloning `node_modules` into Docker context / committing `frontend/out`:** `.gitignore` already covers `frontend/out/`, `frontend/.next/`, `backend/static/`; add a `.dockerignore` in Phase 6.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE framing, keep-alive, no-cache headers | Manual `StreamingResponse` with `data: ...\n\n` strings | `fastapi.sse.EventSourceResponse` + `ServerSentEvent` | Built in since 0.135.0; sets headers and 15 s ping; JSON-encodes dicts |
| Correlated normals | Manual factor model loops | `numpy.linalg.cholesky(C)`; `L @ z` | One matrix product; PD verified |
| Reconnect logic | Custom retry/backoff in JS | Native `EventSource` + server `retry:` | Spec behaviour; matches the E2E reconnect test |
| Static file serving with `index.html` | Custom route returning `FileResponse` | `StaticFiles(html=True)` | Handles `/`, MIME types, 404s, ranges |
| Tailwind theme | Hand-written CSS variable system | `@theme` in `globals.css` | Generates utilities and variables |
| Number formatting | String slicing | `Number.prototype.toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2})` | Thousands separators |

**Key insight:** this phase is mostly assembly of well-supported primitives; the risk is in environment and lifecycle details (shutdown, ports, WSL/Windows boundary), not algorithms.

## Common Pitfalls

### Pitfall 1: uvicorn never exits while an SSE client is connected
**What goes wrong:** SIGINT/SIGTERM prints "Waiting for connections to close" and the process stays up (observed >15 s with a curl client attached).
**Why it happens:** uvicorn waits for open connections before running lifespan shutdown; the SSE generator never finishes by itself. `lifespan` teardown runs after the wait, so a stop-flag set in lifespan cannot help.
**How to avoid:** run uvicorn with `--timeout-graceful-shutdown 2` (verified: exits in ~2 s, logs "Cancel 1 running task(s), timeout graceful shutdown exceeded", lifespan shutdown runs, then a `CancelledError` traceback from the stream task - cosmetic). Put the flag in documented dev/run commands and update the `Dockerfile` CMD (currently `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`; Phase 6 owns the Dockerfile, but Phase 1 should record this so it is not lost; a one-line change now is also fine).
**Warning signs:** `docker stop` takes 10 s then SIGKILLs; test runs leave orphan uvicorn processes.

### Pitfall 2: TypeScript 7 breaks ESLint
**What goes wrong:** `npx eslint` crashes: `Error: typescript-eslint does not support TS 7.0`. `typescript` `latest` on npm is 7.0.2.
**How to avoid:** `npm install -D typescript@~5.9`. Verified with 5.9.3: `eslint` exits clean (only warnings for anonymous default exports), `tsc --noEmit` passes, `next build` passes. TS 6.0.x exists but was not tested.

### Pitfall 3: Port 8000 is occupied by an old `finally` Docker container
**What goes wrong:** curl/Playwright to `localhost:8000` answers `{"status":"ok"}` from the stale container, hiding that the new server never started (this happened during research: my proxied requests hit the old container).
**How to avoid:** run verification on a different port (`--port 8010`) and use `BASE_URL`; or `docker stop finally` first (the container belongs to the user, so prefer the other port, or ask). Also `next dev` rewrite destination is `localhost:8000`; for dev with a different port edit config or stop the container.

### Pitfall 4: Environment variables do not reach the Windows `node`/`npm`
**What goes wrong:** `API_ORIGIN=... npm run dev` or `BASE_URL=... npx playwright test` from WSL does not set the variable inside the Windows process (confirmed: an env override was silently ignored).
**How to avoid:** do not rely on env for the frontend; hardcode defaults, or export `WSLENV=VAR1:VAR2` alongside the variable. Python (`uv run`) runs natively in WSL so `STATIC_DIR` works there.

### Pitfall 5: `StaticFiles` raises at import when the export dir is missing
`RuntimeError: Directory 'static' does not exist` would break tests and API-only dev runs. Use `check_dir=False` (verified) and let missing files 404.

### Pitfall 6: Testing infinite SSE through httpx ASGITransport
A streaming response that never ends cannot be consumed incrementally through `httpx.ASGITransport` (it buffers the full body) [ASSUMED - well known, not re-verified here]. Put the event-producing logic in a plain async generator (`price_events(cache, interval)`) that tests can drive with `anext()`; verify the HTTP layer with curl against a real server.

### Pitfall 7: Direction `flat` and no visible movement
`PriceCache` rounds to 2 dp. With realistic `dt`, one tick moves about 1 cent on a $190 stock, so many ticks are `flat` (no flash) and `V` or `JPM` may sit still for several ticks. This is expected and still satisfies the E2E "price changes within 15 s". Do not "fix" it by inflating volatility; the shock events provide the drama.

### Pitfall 8: Reconnect semantics of EventSource
`retry:` is only learned after a successful connection; the first reconnect delay after a failed initial connect is the browser default (about 3 s in Chromium). A network-level failure (including Playwright `route.abort()`) puts `readyState` at `CONNECTING` (retrying) rather than `CLOSED`; only HTTP errors or wrong content type close the stream permanently. Hence `onerror` -> `reconnecting` unless `CLOSED`, matching the UI-SPEC and `06-sse-reconnect.spec.ts` (expects `reconnecting` with 2+ blocked attempts within 15 s). [CITED: HTML living standard EventSource; consistent with the E2E spec comments]
React StrictMode in `next dev` mounts effects twice, creating and closing an EventSource briefly; harmless because cleanup calls `es.close()`.

### Pitfall 9: `01-fresh-start.spec.ts` expects `cash-balance` 10000 and `total-value` 10000
UI-SPEC deliberately shows `--` in Phase 1 (no fake data). That E2E test is Phase 6 scope and depends on Phase 3; do not satisfy it in Phase 1. The health test and "prices stream and update" test in the same file can pass at the end of Phase 1.

### Pitfall 10: Hot path on `node_modules` from WSL
`npm install` on `/mnt/c` is slow and produces Windows-native binaries; never run `npm`/`next` from a Linux-only path, and never run Linux `node` against that `node_modules`. `next build` rewrites `tsconfig.json` on first run (adds `.next/dev/types/**/*.ts`); commit the resulting file and ignore `next-env.d.ts`.

## Runtime State Inventory

Not applicable (greenfield: `backend/` and `frontend/` do not exist). One stateful item found in the environment: Docker container `finally` (image `finally`, up) bound to host port 8000 (see Pitfall 3). Nothing else stores or registers project state.

## Code Examples

### GBM engine step (shape)
```python
# backend/app/market/simulator.py
class GBMSimulator:
    DEFAULT_DT = 0.5 / (252 * 6.5 * 3600)

    def __init__(self, tickers, dt=DEFAULT_DT, event_probability=0.001, seed=None):
        self._rng = np.random.default_rng(seed)
        self._py_rng = random.Random(seed)
        ...

    def step(self) -> dict[str, float]:
        z = self._rng.standard_normal(len(self._tickers))
        if self._cholesky is not None:
            z = self._cholesky @ z
        for i, t in enumerate(self._tickers):
            mu, sigma = self._params[t]["mu"], self._params[t]["sigma"]
            self._prices[t] *= math.exp((mu - 0.5 * sigma**2) * self._dt + sigma * math.sqrt(self._dt) * z[i])
            if self._py_rng.random() < self._event_prob:
                self._prices[t] *= 1 + self._py_rng.uniform(0.02, 0.05) * self._py_rng.choice([-1, 1])
        return {t: round(p, 2) for t, p in self._prices.items()}
```

### Data source loop and lifecycle
```python
# backend/app/market/simulator_source.py
async def start(self, tickers):
    self._sim = GBMSimulator(tickers, event_probability=self._event_prob)
    for t in tickers:
        self._cache.update(t, self._sim.get_price(t))   # seed = session open
    self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

async def stop(self):
    if self._task:
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
```
Keep a strong reference to the task (it is stored on `self._task`); asyncio only holds weak references.

### eslint.config.mjs (verified with eslint 10.13.0 + eslint-config-next 16.4.2)
```js
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "out/**", "next-env.d.ts"]),
]);
```

### pytest config
```toml
# backend/pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
```
`asyncio_mode` defaults to strict if unset [CITED: pytest-asyncio.readthedocs.io configuration]. Add `pythonpath = ["."]` if `import app` fails (pytest rootdir usually suffices with `uv run pytest` from `backend/`; with a virtual project the package is not installed, so `pythonpath = ["."]` is the safe setting).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sse-starlette` / manual `StreamingResponse` | `fastapi.sse.EventSourceResponse` | FastAPI 0.135.0 | No extra dependency; keep-alive and headers built in |
| `tailwind.config.js` + `@tailwind base/...` | `@import "tailwindcss"` + `@theme` + `@tailwindcss/postcss` | Tailwind 4 | CSS-first config |
| `next lint` | plain `eslint` with flat config (`eslint-config-next/core-web-vitals`) | Next 16 | `lint` script is `eslint` |
| `next export` | `output: 'export'` | Next 13.3/14 | already standard |
| `pytest-asyncio` strict-only habits | `asyncio_mode = "auto"` + explicit loop-scope settings | pytest-asyncio 1.x | one config line removes decorators |

**Deprecated/outdated:** the `lightweight-charts` 5.x API differs from 4.x (`chart.addSeries(LineSeries, ...)`); relevant only from Phase 2.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `httpx.ASGITransport` buffers an infinite streaming response, so SSE must be tested by driving the generator directly | Pitfall 6 | Low: the generator-level test is valid either way; only the justification changes |
| A2 | TypeScript 6.0.x would be compatible with `typescript-eslint` 8.71 (not tested; pin is ~5.9) | Standard Stack | None if the pin is kept |
| A3 | Optional Playwright smoke (`BASE_URL`, browsers installed in `test/node_modules`) may work from WSL via the Windows wrappers | Validation | Low: it is optional; curl/grep checks are the primary gate |
| A4 | slopcheck was not run; packages are tagged approved because they are named in official docs and the locked stack | Package Legitimacy Audit | Very low |

## Open Questions (RESOLVED)

1. **Should the `Dockerfile` CMD gain `--timeout-graceful-shutdown 2` in Phase 1 or Phase 6?**
   - What we know: needed for clean `docker stop`; Dockerfile is "scaffolding kept" but Phase 6 owns Docker.
   - Recommendation: add the flag in Phase 1 documentation/run commands; edit the Dockerfile in Phase 1 only if the planner wants a one-line task, else queue for Phase 6.
   - RESOLVED: flag goes in Phase 1 run/verify commands and the README (01-05); the Dockerfile is not edited until Phase 6.
2. **What to do with the stale `finally` container on port 8000?**
   - Recommendation: do not stop it automatically (user's); verify on port 8010. Mention in the plan's verification notes.
   - RESOLVED: container left alone; all Phase 1 verification uses ports 8010/8011 (01-01, 01-02, 01-03, 01-05).
3. **Whether `PriceUpdate` keeps the old `change`/`change_percent` extras.**
   - Recommendation: drop them; contract is `ticker, price, previous_price, timestamp, direction, day_change_pct` and later phases use `day_change_pct`.
   - RESOLVED: dropped; `PriceUpdate.to_dict()` emits exactly the six locked keys (01-01).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | backend | yes | 0.13.1 | - |
| Python 3.14 | backend | yes (uv resolves 3.14.8; scratch project created and ran) | 3.14 | - |
| node / npm (Windows wrappers) | frontend | yes | Node 24.21.0, npm 11.19 | - |
| curl (WSL) and curl.exe (Windows) | smoke checks | yes | - | - |
| Docker | Phase 6 only | yes; container `finally` running on 8000 | - | - |
| Playwright (test/node_modules) | optional E2E smoke | binaries present in `test/node_modules/.bin`; browsers not checked | 1.64.1 | curl/grep gates |
| Port 8000 | default run | **occupied** by old `finally` container | - | use 8010 for verification |

WSL curl reaches WSL-hosted servers; `curl.exe` reaches Windows-hosted `next dev` (WSL curl to a Windows-bound port returned 000 in one early attempt). Use `curl.exe` for `next dev` checks.

**Missing dependencies with no fallback:** none.

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio 1.4.0 (backend); eslint 10 + `tsc --noEmit` + `next build` (frontend, no unit tests until TEST-05) |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` (Wave 0); `frontend/eslint.config.mjs` (Wave 0) |
| Quick run command | `cd backend && uv run pytest -x -q` |
| Full suite command | `cd backend && uv run pytest -q` then `cd frontend && npm run lint && npm run typecheck && npm run build` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MKT-01 | `SimulatorDataSource` is a `MarketDataSource`; factory returns it; abstract class cannot be instantiated | unit | `cd backend && uv run pytest tests/market/test_interface.py -x -q` | Wave 0 |
| MKT-02 | `step()` returns all tickers, positive, 2 dp, changes over time; with `event_probability=0` log-return mean/std match `(mu - sigma^2/2)dt` and `sigma*sqrt(dt)` within tolerance (large n, seeded) | unit | `uv run pytest tests/market/test_simulator.py -x -q` | Wave 0 |
| MKT-03 | Cholesky exists and PD for 10 default tickers; realised correlation tech pair ~0.6, cross-sector ~0.3 (seeded, 50k steps with dt scaled up or direct `L @ z` sampling), `_cholesky is None` for one ticker | unit | `uv run pytest tests/market/test_simulator.py -k correlation -q` | Wave 0 |
| MKT-04 | with `event_probability=1.0` every ticker moves at least about 2% per step | unit | `uv run pytest tests/market/test_simulator.py -k event -q` | Wave 0 |
| MKT-05 | Seed prices equal the table (AAPL 190, GOOGL 175, ...); unknown ticker gets 50-300 | unit | `uv run pytest tests/market/test_simulator.py -k seed -q` | Wave 0 |
| MKT-08 | Cache: first update `flat`, previous price tracked, `direction`, `day_change_pct` against session open, version bumps, `remove`, rounding | unit | `uv run pytest tests/market/test_cache.py -x -q` | Wave 0 |
| MKT-08 | Source: `start()` seeds cache before returning; background loop updates; `stop()` idempotent and cancels; add/remove ticker reaches cache; loop survives a step exception | async unit | `uv run pytest tests/market/test_source.py -x -q` | Wave 0 |
| STRM-02/03 | `price_events` generator: first call yields all 10 tickers with required keys; does not yield again if version unchanged; yields after update; first event carries retry | async unit | `uv run pytest tests/market/test_stream.py -x -q` | Wave 0 |
| STRM-01/04 | Real server returns `text/event-stream`, `retry: 1000`, repeated `data:` frames | smoke (curl) | see "Server smoke" below | script in plan |
| OPS-02 | `/api/health` returns exactly `{"status":"ok"}` | unit (httpx ASGITransport, no stream) + curl | `uv run pytest tests/test_health.py -q`; `curl -s localhost:8010/api/health` | Wave 0 |
| OPS-01 | `/` served from the export; `/api/*` unaffected; unknown path 404 | smoke (curl) | see below | script in plan |
| UI-01 | Export builds; Tailwind theme tokens present in emitted CSS | build | `cd frontend && npm run build && grep -l "color-bg" out/_next/static/chunks/*.css` | Wave 0 |
| UI-03/UI-04 | Rows and test ids exist in the static HTML before any price arrives; no pure black/white used | build + grep | `grep -c "watchlist-row-" frontend/out/index.html` (expect 10 distinct) and `grep -o 'data-testid="connection-status"' frontend/out/index.html` | Wave 0 |
| UI-03/04 | Lint and types clean | static | `cd frontend && npm run lint && npm run typecheck` | Wave 0 |

Manual-only (with justification): visual flash/fade fidelity, sparkline appearance, dot pulse, layout at 1600x1000 and tablet width - require a browser; checked by the optional Playwright smoke or by a human at the Phase 1 verify-work step (screenshot).

**Server smoke (copy into a verification task; port 8010 avoids the stale container):**
```bash
cd /mnt/c/Users/fulai/projects/finally/backend
STATIC_DIR=../frontend/out uv run uvicorn app.main:app --port 8010 --timeout-graceful-shutdown 2 &
sleep 3
curl -s localhost:8010/api/health                                   # {"status":"ok"}
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" localhost:8010/   # 200 text/html
curl -s -N -m 3 localhost:8010/api/stream/prices | head -c 600      # retry: 1000 + data: {"AAPL": {...}} frames
curl -s -N -m 4 localhost:8010/api/stream/prices | grep -c '^data:' # >= 6 frames in 4 s (~500 ms cadence)
curl -s -o /dev/null -w "%{http_code}\n" localhost:8010/api/nope    # 404
kill -INT %1; wait                                                  # must exit within about 2 s (shutdown check)
```
Also assert in a small script that one `data:` frame contains all 10 default tickers and each value has the six required keys (`uv run python -c` reading the first frame, or a pytest marked as integration that starts uvicorn via subprocess).

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest -x -q` (backend tasks) or `cd frontend && npm run lint && npm run typecheck` (frontend tasks)
- **Per wave merge:** full suite command plus the Server smoke block
- **Phase gate:** full suite green, `npm run build` succeeds, Server smoke passes with `STATIC_DIR=../frontend/out`, human eyeball of the running page (or Playwright smoke), before `/gsd:verify-work`

### Optional browser smoke (against the already running server)
`cd test && WSLENV=BASE_URL BASE_URL=http://localhost:8010 npx playwright test e2e/06-sse-reconnect.spec.ts` and the `health` and `prices stream and update` tests of `01-fresh-start.spec.ts` (`-g "health|prices stream"`). These use `connection-status`, `price-AAPL` and the aborted-stream route; expected to pass at the end of Phase 1. Not a gate (A3); `fresh start ... $10,000` must be excluded (Pitfall 9).

### Wave 0 Gaps
- [ ] `backend/pyproject.toml` pytest config (`asyncio_mode = "auto"`, `pythonpath = ["."]`)
- [ ] `backend/tests/market/` files: `test_interface.py`, `test_simulator.py`, `test_cache.py`, `test_source.py`, `test_stream.py`; `backend/tests/test_health.py`
- [ ] `frontend/eslint.config.mjs`, `package.json` scripts (`lint`, `typecheck`, `build`)
- [ ] Framework install: `uv add --dev pytest pytest-asyncio httpx`; `npm install -D eslint eslint-config-next typescript@~5.9`

## Security Domain

`security_enforcement` is not set to false in `.planning/config.json`, so it is enabled. This phase has no authentication, no user input, no database and no secrets; it is a read-only price stream on localhost.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (single-user by design, out of scope) | - |
| V3 Session Management | no | - |
| V4 Access Control | no | - |
| V5 Input Validation | minimal: no request body or query params this phase; `/api/stream/prices` and `/api/health` take none. Phase 2 adds ticker validation | FastAPI/pydantic when input arrives |
| V6 Cryptography | no | - |
| V12/V14 Config and files | yes: static mount | `StaticFiles` rooted at `STATIC_DIR` (Starlette resolves and rejects path traversal); do not mount the repo root or `db/` |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via static route | Information disclosure | Use `StaticFiles` (not a custom file handler); mount only the export directory |
| Unbounded SSE connections exhausting the server | Denial of service | Acceptable for a single-user local app; per-connection loop is cheap (reads cache). Not mitigated further (YAGNI) |
| Leaking `.env` / API keys into the static export | Information disclosure | No secrets in the frontend; never use `NEXT_PUBLIC_` for keys; `.env` stays gitignored |
| Leaking `node_modules`/`.env` into Docker context | Information disclosure | `.dockerignore` (Phase 6) |

## Sources

### Primary (HIGH confidence)
- fastapi.tiangolo.com/tutorial/server-sent-events and /reference/sse - `EventSourceResponse`, `ServerSentEvent` fields, built-in ping/no-cache/X-Accel-Buffering, added in 0.135.0
- nextjs.org/docs/app/guides/static-exports (lastUpdated 2026-08-09) - `output: 'export'`, unsupported features list including Rewrites
- tailwindcss.com/docs/installation/framework-guides/nextjs - packages, `postcss.config.mjs`, `@import "tailwindcss"`
- pytest-asyncio.readthedocs.io configuration - `asyncio_mode` default strict, loop-scope options
- npm registry (`npm view`) and PyPI JSON queried 2026-10-19 for all versions
- Runs in this session: Next 16.4.2 build + dev (naive vs phase-aware config), Tailwind `@theme` output, FastAPI SSE route (curl headers/frames), StaticFiles behaviour, uvicorn shutdown with and without `--timeout-graceful-shutdown`, numpy 2.5.4 Cholesky and realised correlation, ESLint 10 + eslint-config-next 16.4.2 with TS 7.0.2 vs 5.9.3, hook/PriceCell lint and typecheck

### Secondary (MEDIUM confidence)
- `planning/MARKET_INTERFACE.md`, `planning/MARKET_SIMULATOR.md` (project design docs, adopted by CONTEXT.md)
- `test/e2e/*.spec.ts`, `test/playwright.config.ts`, `Dockerfile` (read directly)

### Tertiary (LOW confidence)
- None relied on for decisions (the httpx ASGITransport buffering claim is A1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions queried today and every package exercised in a scratch project
- Architecture: HIGH - patterns executed (SSE route, static mount, dev proxy, shutdown) rather than only read
- Pitfalls: HIGH - shutdown hang, TS 7/eslint break, stale container, and WSLENV issue were all observed first hand; EventSource reconnect nuance is spec-based (MEDIUM)

**Research date:** 2026-10-19
**Valid until:** 2026-11-18 (fast-moving: Next, FastAPI and TypeScript ship frequently; re-check the TypeScript/eslint pin before upgrading)
