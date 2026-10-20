---
phase: 5
slug: real-market-data-massive
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-20
---

# Phase 5 — Validation Strategy

> Per-phase validation contract. Full requirement-to-command map: `05-RESEARCH.md` "Validation Architecture" (authoritative; summarized here).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1 + pytest-asyncio (auto) + httpx ASGITransport; fake Massive client (no network); eslint + tsc + next build; Playwright regression |
| **Config file** | `backend/pyproject.toml`, `test/playwright.config.ts` |
| **Quick run command** | `cd backend && ~/.local/bin/uv run pytest tests/market -q` |
| **Full suite command** | `cd backend && ~/.local/bin/uv run pytest -q && cd ../frontend && npm run lint && npm run typecheck && npm run build` |
| **Estimated runtime** | ~70 seconds |

---

## Sampling Rate

- **After every task commit:** `tests/market` pytest (backend) or lint + typecheck (frontend)
- **After every plan wave:** full suite command
- **Before `/gsd:verify-work`:** full suite, plus the Playwright 01-06 regression on a fresh simulator server started with `MASSIVE_API_KEY=` and `LLM_MOCK=true`
- **Max feedback latency:** 70 seconds

---

## Requirement Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| MKT-06 | non-empty key -> MassiveDataSource; empty / whitespace / unset -> simulator; MASSIVE_POLL_INTERVAL parsed | unit | `uv run pytest tests/market/test_factory.py -q` | ❌ W0 | ⬜ pending |
| MKT-06 | `/api/health` -> `{"status":"ok","source":"simulator"}` under tests (key blanked in conftest) | integration | `uv run pytest tests/test_health.py -q` | ✅ (update) | ⬜ pending |
| MKT-07 | snapshot price preference last_trade > min > day > prev_day; zero/None skipped | unit | `uv run pytest tests/market/test_massive_parse.py -k quote -q` | ❌ W0 | ⬜ pending |
| MKT-07 | grouped bars step back over today-403 and empty weekend; give up after 5; other BadResponse raises | unit | `uv run pytest tests/market/test_massive_parse.py -k grouped -q` | ❌ W0 | ⬜ pending |
| MKT-07 | snapshot NOT_AUTHORIZED -> EOD mode once, interval >= 900, only tracked tickers cached, `"stocks"` string used | unit | `uv run pytest tests/market/test_massive_source.py -k "fallback or eod" -q` | ❌ W0 | ⬜ pending |
| MKT-07 | poll exception logged; loop runs the next poll | unit | `uv run pytest tests/market/test_massive_source.py -k survives -q` | ❌ W0 | ⬜ pending |
| MKT-07 | `PriceCache.update(reference=...)` drives day change %; simulator unchanged | unit | `uv run pytest tests/market/test_cache.py -q` | ✅ (extend) | ⬜ pending |
| MKT-09 | ns/ms -> seconds; cached timestamp equals source time, never `time.time()` | unit | `uv run pytest tests/market/test_massive_parse.py tests/market/test_massive_source.py -k timestamp -q` | ❌ W0 | ⬜ pending |
| MKT-09 | `add_ticker` prices a new ticker at once (snapshot single / EOD cached bar or prev close); no call if already tracked; failure -> no cache entry | unit | `uv run pytest tests/market/test_massive_source.py -k add_ticker -q` | ❌ W0 | ⬜ pending |
| MKT-09 | `EOD · as of <date>` badge only when newest timestamp > 5 min old; no `Date.now()` in render | static | `cd frontend && npm run lint && npm run typecheck && npm run build` | ✅ | ⬜ pending |
| Regression | whole backend suite never touches the network (real key in `.env`) | pytest | `cd backend && uv run pytest -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Simulator smoke (port 8032+, scratch DB_PATH, `MASSIVE_API_KEY=` set explicitly, stop by recorded PID, never `pkill -f uvicorn`): GET `/api/health` -> `source: simulator`; no badge in the header.

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py`: `os.environ["MASSIVE_API_KEY"] = ""` before `from app import main` (the repo `.env` holds a real key; load_dotenv does not override)
- [ ] `backend/tests/market/test_massive_parse.py`, `test_massive_source.py` (with a `FakeClient` built on real SDK models via `from_dict`), `test_factory.py`
- [ ] `cd backend && ~/.local/bin/uv add massive` (2.9.0)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live EOD prices from the free key | MKT-06, MKT-07 | Needs the user's key and the real API | Optional: start on port 8033 with the `.env` key; `/api/health` shows `source: massive`; prices match the last close; never print the key |
| Badge appearance and new-ticker instant price | MKT-09 | Visual, live API | In the live smoke, the header shows `EOD · as of <date>`; adding a ticker shows its price without waiting 15 min |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 70s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
