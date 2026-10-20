---
phase: 1
slug: live-price-terminal
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-19
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `01-RESEARCH.md` "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (backend); eslint 10 + `tsc --noEmit` + `next build` (frontend; no unit tests until TEST-05) |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` (Wave 0); `frontend/eslint.config.mjs` (Wave 0) |
| **Quick run command** | `cd backend && uv run pytest -x -q` |
| **Full suite command** | `cd backend && uv run pytest -q` then `cd frontend && npm run lint && npm run typecheck && npm run build` |
| **Estimated runtime** | ~60 seconds (backend ~10s, frontend build ~45s) |

---

## Sampling Rate

- **After every task commit:** `cd backend && uv run pytest -x -q` (backend tasks) or `cd frontend && npm run lint && npm run typecheck` (frontend tasks)
- **After every plan wave:** full suite command plus the Server smoke block below
- **Before `/gsd:verify-work`:** full suite green, `npm run build` succeeds, Server smoke passes with `STATIC_DIR=../frontend/out`
- **Max feedback latency:** 60 seconds

---

## Requirement Verification Map

Task IDs are assigned by the planner; each plan task must reference the command for its requirement.

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| MKT-01 | `SimulatorDataSource` is a `MarketDataSource`; factory returns it; ABC not instantiable | unit | `cd backend && uv run pytest tests/market/test_interface.py -x -q` | ❌ W0 | ⬜ pending |
| MKT-02 | `step()` returns all tickers, positive, 2 dp; GBM log-return mean/std match theory (seeded, events off) | unit | `cd backend && uv run pytest tests/market/test_simulator.py -x -q` | ❌ W0 | ⬜ pending |
| MKT-03 | Cholesky PD for defaults; realised correlation tech ~0.6, cross-sector ~0.3 | unit | `cd backend && uv run pytest tests/market/test_simulator.py -k correlation -q` | ❌ W0 | ⬜ pending |
| MKT-04 | `event_probability=1.0` moves every ticker at least ~2% | unit | `cd backend && uv run pytest tests/market/test_simulator.py -k event -q` | ❌ W0 | ⬜ pending |
| MKT-05 | Seed prices match table; unknown ticker gets 50-300 | unit | `cd backend && uv run pytest tests/market/test_simulator.py -k seed -q` | ❌ W0 | ⬜ pending |
| MKT-08 | Cache: previous price, direction, `day_change_pct` vs session open, version bump, remove | unit | `cd backend && uv run pytest tests/market/test_cache.py -x -q` | ❌ W0 | ⬜ pending |
| MKT-08 | Source: start seeds cache, loop updates, stop idempotent, add/remove reach cache | async unit | `cd backend && uv run pytest tests/market/test_source.py -x -q` | ❌ W0 | ⬜ pending |
| STRM-02/03 | Event generator yields all tickers with the 6 keys; no yield if version unchanged; retry on first event | async unit | `cd backend && uv run pytest tests/market/test_stream.py -x -q` | ❌ W0 | ⬜ pending |
| STRM-01/04 | Real server returns `text/event-stream`, `retry: 1000`, repeated `data:` frames | smoke | Server smoke (below) | script | ⬜ pending |
| OPS-02 | `/api/health` returns exactly `{"status":"ok"}` | unit + smoke | `cd backend && uv run pytest tests/test_health.py -q` | ❌ W0 | ⬜ pending |
| OPS-01 | `/` served from export; `/api/*` unaffected; unknown path 404 | smoke | Server smoke (below) | script | ⬜ pending |
| UI-01 | Export builds; theme tokens in emitted CSS | build | `cd frontend && npm run build && grep -l "color-bg" out/_next/static/chunks/*.css` | ❌ W0 | ⬜ pending |
| UI-03/04 | 10 `watchlist-row-` ids and `connection-status` in static HTML | build + grep | `grep -o 'data-testid="watchlist-row-[A-Z]*"' frontend/out/index.html \| sort -u \| wc -l` (expect 10) | ❌ W0 | ⬜ pending |
| UI-03/04 | Lint and types clean | static | `cd frontend && npm run lint && npm run typecheck` | ❌ W0 | ⬜ pending |
| TEST-01 | All market data tests above pass | unit | `cd backend && uv run pytest tests/market -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Server smoke (port 8010; host port 8000 is held by an old `finally` container)

```bash
cd /mnt/c/Users/fulai/projects/finally/backend
STATIC_DIR=../frontend/out uv run uvicorn app.main:app --port 8010 --timeout-graceful-shutdown 2 &
sleep 3
curl -s localhost:8010/api/health                                    # {"status":"ok"}
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" localhost:8010/   # 200 text/html
curl -s -N -m 4 localhost:8010/api/stream/prices | grep -c '^data:'  # >= 6 frames in 4 s
curl -s -o /dev/null -w "%{http_code}\n" localhost:8010/api/nope     # 404
kill -INT %1; wait                                                   # exits within ~2 s
```

---

## Wave 0 Requirements

- [ ] `backend/pyproject.toml` pytest config (`asyncio_mode = "auto"`, `pythonpath = ["."]`)
- [ ] `backend/tests/market/test_interface.py`, `test_simulator.py`, `test_cache.py`, `test_source.py`, `test_stream.py`; `backend/tests/test_health.py`
- [ ] `frontend/eslint.config.mjs`, `package.json` scripts `lint`, `typecheck`, `build`
- [ ] `uv add --dev pytest pytest-asyncio httpx`; `npm install -D eslint eslint-config-next typescript@~5.9`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flash fades over ~500ms, sparkline fills progressively, dot pulse | UI-03, UI-04 | Visual timing needs a browser | Open http://localhost:8010, watch 10 s; optional: `cd test && WSLENV=BASE_URL BASE_URL=http://localhost:8010 npx playwright test e2e/06-sse-reconnect.spec.ts` and `e2e/01-fresh-start.spec.ts -g "health\|prices stream"` |
| Page resumes streaming after backend restart | STRM-04 | Needs a live browser across a server restart | Restart uvicorn while page open; dot goes yellow then green, prices resume without reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
