# Testing Patterns

**Analysis Date:** 2026-10-19

Scope: backend pytest suite and Playwright E2E in `test/`. `frontend/` is absent (deleted in commit 4619f5b), so there are no frontend unit tests; the E2E specs depend on frontend `data-testid` hooks that must be recreated.

## Test Framework

**Backend runner:**
- pytest >=8.3 with pytest-asyncio >=0.24, pytest-cov, httpx (FastAPI `TestClient`)
- Config: `[tool.pytest.ini_options]` in `backend/pyproject.toml` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`, function-scoped loops)
- Assertions: plain `assert`, `pytest.approx` for floats, `pytest.raises` for errors

**E2E runner:** Playwright 1.64.1 (`test/package.json`), Chromium only, config `test/playwright.config.ts` (serial, 1 worker, 30s timeout, 10s expect timeout, trace and screenshot on failure, `BASE_URL` default `http://localhost:8000`).

**Run commands:**
```bash
cd backend && uv sync --extra dev
uv run pytest -v                     # All backend tests (169 pass, ~12s)
uv run pytest --cov=app              # Coverage
uv run ruff check app/ tests/        # Lint
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright   # E2E (from repo root)
cd test && npx playwright test       # E2E against a locally running app (LLM_MOCK=true, fresh DB_PATH)
```

## Test File Organization

Tests live in `backend/tests/`, mirroring `backend/app/` packages, each with `__init__.py`:

```
backend/tests/
├── conftest.py            # docstring only
├── api/test_routes.py
├── db/{conftest,test_init,test_repository}.py
├── llm/{conftest,test_chat,test_mock,test_parsing,test_router}.py
├── market/test_{cache,factory,massive,models,simulator,simulator_source}.py
└── portfolio/test_{concurrency,trading,watchlist}.py
test/e2e/{01-fresh-start,02-watchlist,03-trading,04-portfolio-viz,05-chat,06-sse-reconnect}.spec.ts + helpers.ts
```

Naming: `test_<topic>.py`, functions `test_<behavior>`. E2E: numbered `NN-topic.spec.ts` (order matters; `01` expects a fresh DB).

## Test Structure

Mostly flat module-level test functions (classes allowed by config but rarely used). One-line module docstring states scope. Async tests are plain `async def` (no decorator needed due to `asyncio_mode = "auto"`):

```python
async def test_failed_trade_reported(mock_mode, cache, source):
    body = await chat.handle_chat("sell 5 AAPL", cache, source)
    trade = body["trades"][0]
    assert trade["status"] == "failed" and trade["error"] and trade["price"] is None
    assert db.get_cash() == 10000.0
```

API tests build a minimal `FastAPI()` app, include only the routers under test, and use `TestClient` (`backend/tests/api/test_routes.py`); they assert on status codes and response shapes (`set(body["trade"]) >= {...}`).

## Mocking and Isolation

**Database:** real SQLite, never mocked. Each test gets a fresh file via `monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))` then `db.init_db()`. Autouse fixtures do this in `backend/tests/db/conftest.py` (`tmp_db`) and `backend/tests/llm/conftest.py` (`fresh_db`); other packages inline it in their fixture.

**Market data:** use a real `PriceCache` seeded by hand (`cache.update("AAPL", 100.0)`), not the simulator.

**Market source:** hand-written fakes recording calls (`FakeSource` in `backend/tests/llm/conftest.py` with `added`/`removed` lists and async `add_ticker`/`remove_ticker`).

**LLM:** `LLM_MOCK` env var switches to deterministic `backend/app/llm/mock.py` responses (`monkeypatch.setenv("LLM_MOCK", "true")`, wrapped in a `mock_mode` fixture). Real-path tests set `LLM_MOCK=false` and patch the `call_llm` callable. No test hits the network.

**Massive SDK:** `unittest.mock.patch`/`MagicMock` only for the REST client; response data is built from real SDK model classes (`TickerSnapshot.from_dict`, `GroupedDailyAgg.from_dict`) via small `_snap`/`_bar` helper builders in `backend/tests/market/test_massive.py`.

**Rule:** prefer `monkeypatch` over global patching; mock only external boundaries (LLM, Massive HTTP, market source). Do not mock the DB or `PriceCache`.

## Fixtures and Factories

Shared fixtures: `cache` (PriceCache with AAPL at 100.0) and `source` in `backend/tests/llm/conftest.py`; `client` in `backend/tests/api/test_routes.py` (duplicates `cache`/`FakeSource` locally). Prices are round numbers (100.0) so cash arithmetic is exact (buy 10 -> cash 9000.0). Helper builders are module-private functions prefixed `_`. No fixtures directory or factory library.

## Concurrency Tests

`backend/tests/portfolio/test_concurrency.py` uses `threading.Barrier` plus a monkeypatched `db.get_cash` to force a read-before-write race, then asserts exactly one of two overspending buys succeeds. Use this pattern for any new transactional logic.

## E2E Patterns (`test/e2e/`)

- Shared state: one app, one DB, serial execution; specs must be tolerant of prior state (read "before" values and assert deltas, e.g. `heldQuantity` before/after).
- Helpers in `test/e2e/helpers.ts`: `openApp` (goto `/` then wait for `connection-status` with `data-status="connected"`), `apiTrade`/`ensureNotWatched`/`heldQuantity` (set up or verify via `request` API context), `uiTrade`, `readNumber`/`parseMoney`.
- Selectors: `page.getByTestId(...)` exclusively. Required ids include `connection-status`, `cash-balance`, `trade-ticker`, `trade-quantity`, `buy-button`, `sell-button`, `trade-error`, `position-row-<TICKER>`.
- Async UI settling uses `await expect.poll(() => ...)` and web-first `expect(locator)` assertions, never fixed sleeps.
- Runs with `LLM_MOCK=true`. Docker infra: `test/docker-compose.test.yml` (app with tmpfs DB + Playwright container); details in `test/README.md`. Artifacts `test/playwright-report/`, `test/test-results/`, `test/node_modules/` are untracked (`test/.gitignore`).

## Coverage

No enforced threshold. `[tool.coverage]` in `backend/pyproject.toml` sources `app`, omits `tests/*`, excludes `pragma: no cover`, `__repr__`, `NotImplementedError`, `__main__` blocks. No coverage gate in CI (`.github/workflows/` only holds Claude review workflows, no test job).

## Test Types

- Unit: market (simulator GBM, cache, models, factory, Massive parsing), portfolio math, repository, LLM parsing.
- Integration: DB-backed trading, chat orchestration, route tests via `TestClient`.
- E2E: Playwright against the full container (currently cannot pass until the frontend is rebuilt).
- Frontend unit tests: Not present (frontend deleted).

## Common Patterns

**Error testing:**
```python
with pytest.raises(TradeError):
    execute_trade("AAPL", "sell", 1, cache)
assert db.get_cash() == 10000.0   # state unchanged after rejection
```

**Float assertions:** `assert db.get_cash() == pytest.approx(4000.0)`.

**Adding a test:** place it in the matching `backend/tests/<package>/test_<module>.py`, reuse the package's `conftest.py` fixtures, isolate DB via `DB_PATH`, run `uv run pytest` and `uv run ruff check app/ tests/`.

---

*Testing analysis: 2026-10-19*
