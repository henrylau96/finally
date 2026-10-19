---
phase: 2
slug: persistent-watchlist-charts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-19
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `02-RESEARCH.md` "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 + pytest-asyncio (auto mode) + httpx ASGITransport (backend); eslint + `tsc --noEmit` + `next build` (frontend) |
| **Config file** | `backend/pyproject.toml`; shared fixture in `backend/tests/conftest.py` (Wave 0: lifespan via `app.router.lifespan_context(app)`, `DB_PATH` = tmp_path file, cache cleared) |
| **Quick run command** | `cd backend && uv run pytest tests -x -q` |
| **Full suite command** | `cd backend && uv run pytest -q` then `cd frontend && npm run lint && npm run typecheck && npm run build` |
| **Estimated runtime** | ~70 seconds |

---

## Sampling Rate

- **After every task commit:** `cd backend && uv run pytest tests -x -q`; frontend tasks also `npm run lint && npm run typecheck`
- **After every plan wave:** full suite command
- **Before `/gsd:verify-work`:** full suite, curl smoke on 8010, Playwright `02-watchlist` spec
- **Max feedback latency:** 70 seconds

---

## Requirement Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| DATA-01 | DB file and parent dir created on first start; second init does not reseed | unit | `cd backend && uv run pytest tests/test_db.py -k init -x` | ❌ W0 | ⬜ pending |
| DATA-02 | six tables exist; `user_id` defaults to 'default' (users_profile uses `id` per PLAN.md) | unit | `cd backend && uv run pytest tests/test_db.py -k schema -x` | ❌ W0 | ⬜ pending |
| DATA-03 | seed: cash 10000, 10 default tickers in order | unit | `cd backend && uv run pytest tests/test_db.py -k seed -x` | ❌ W0 | ⬜ pending |
| WATCH-01 | GET returns rows with ticker, price fields, added_at | api | `cd backend && uv run pytest tests/test_watchlist_api.py -k list -x` | ❌ W0 | ⬜ pending |
| WATCH-02 | POST 201; ticker in GET, source and cache; lowercase accepted; invalid -> 422 | api | `cd backend && uv run pytest tests/test_watchlist_api.py -k "add or invalid" -x` | ❌ W0 | ⬜ pending |
| WATCH-03 | DELETE 204; gone from GET/source/cache; second DELETE 404; persists across lifespan restart | api | `cd backend && uv run pytest tests/test_watchlist_api.py -k "remove or persist" -x` | ❌ W0 | ⬜ pending |
| WATCH-04 | duplicate POST 200, single row | api | `cd backend && uv run pytest tests/test_watchlist_api.py -k duplicate -x` | ❌ W0 | ⬜ pending |
| (edge) | all removed -> GET `[]`; restart with empty watchlist does not reseed | api | `cd backend && uv run pytest tests/test_watchlist_api.py -k empty -x` | ❌ W0 | ⬜ pending |
| UI-05 | add form and remove button built with test ids | build+grep | `cd frontend && npm run build && grep -rl "watchlist-add-input" out/ && grep -rl "watchlist-remove-" out/` | ❌ W0 | ⬜ pending |
| UI-06 | main chart uses lightweight-charts; placeholder copy gone | build+grep | `grep -q '"lightweight-charts"' frontend/package.json && ! grep -r "Select a ticker to see its chart" frontend/src` | ❌ W0 | ⬜ pending |
| UI-05/06 live | add PYPL gets a price, remove it, select MSFT sets `data-ticker` | e2e | `cd test && WSLENV=BASE_URL BASE_URL=http://localhost:8010 npx playwright test e2e/02-watchlist.spec.ts` (server started with a scratch `DB_PATH`) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Server smoke (port 8010; stop by explicit PID, never `pkill -f uvicorn`)

```bash
cd /mnt/c/Users/fulai/projects/finally/backend
DB_PATH=/tmp/finally-p2-smoke.db STATIC_DIR=../frontend/out uv run uvicorn app.main:app --port 8010 --timeout-graceful-shutdown 2 & PID=$!
curl -s -XPOST localhost:8010/api/watchlist -H 'content-type: application/json' -d '{"ticker":"pypl"}' -o /dev/null -w '%{http_code}\n'   # 201
curl -s -XPOST localhost:8010/api/watchlist -H 'content-type: application/json' -d '{"ticker":"PYPL"}' -o /dev/null -w '%{http_code}\n'   # 200
curl -s -XDELETE localhost:8010/api/watchlist/PYPL -o /dev/null -w '%{http_code}\n'   # 204
curl -s -XDELETE localhost:8010/api/watchlist/PYPL -o /dev/null -w '%{http_code}\n'   # 404
kill -INT $PID
```

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` fixture: lifespan context, tmp `DB_PATH`, cache cleared
- [ ] `backend/tests/test_db.py`, `backend/tests/test_watchlist_api.py`
- [ ] `.gitignore`: `db/*.db-wal`, `db/*.db-shm`
- [ ] `npm install lightweight-charts@5.2.1`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chart renders, follows selection, live ticks append, axis formatting | UI-06 | Canvas rendering needs a browser | Open the 8010 server, click several rows, watch 30 s |
| Removed ticker stays removed after restart | WATCH-03 | Covered by pytest lifespan restart; browser confirm optional | Remove a ticker, restart server, reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 70s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
