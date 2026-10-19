# Codebase Structure

**Analysis Date:** 2026-10-19

## Directory Layout

```
finally/
├── backend/                 # uv Python project (FastAPI)
│   ├── app/
│   │   ├── main.py          # ASGI entry, lifespan, static mount
│   │   ├── api/             # health, portfolio, watchlist routers
│   │   ├── db/              # connection.py, repository.py, schema.sql
│   │   ├── llm/             # chat, client, mock, prompt, router, schema
│   │   ├── market/          # interface, cache, models, factory, simulator, massive_client, stream, seed_prices
│   │   └── portfolio/       # trading, watchlist, snapshots
│   ├── tests/               # pytest, mirrors app/ (api, db, llm, market, portfolio)
│   ├── market_data_demo.py  # Rich terminal demo
│   ├── pyproject.toml       # deps, pytest, ruff config
│   ├── uv.lock
│   ├── .python-version
│   ├── CLAUDE.md, README.md
│   └── static/              # (gitignored) frontend build target, absent locally
├── frontend/                # ABSENT - deleted in 4619f5b, to be rebuilt (Next.js static export)
├── test/                    # Playwright E2E project
│   ├── e2e/                 # 01-fresh-start ... 06-sse-reconnect .spec.ts, helpers.ts
│   ├── docker-compose.test.yml
│   ├── playwright.config.ts, package.json, README.md
├── scripts/                 # start/stop for mac(.sh) and windows(.ps1)
├── db/                      # runtime SQLite location (.gitkeep; finally.db gitignored)
├── planning/                # PLAN.md, TEAM_CONTRACT.md, MARKET_*.md, MASSIVE_API.md, archive/
├── .planning/codebase/      # GSD codebase maps
├── .github/workflows/       # claude.yml, claude-code-review.yml
├── .claude/                 # GSD tooling, agents, commands, settings
├── Dockerfile               # 2-stage: node:20-slim -> python:3.14-slim
├── docker-compose.yml       # convenience wrapper, volume finally-data
├── .env / .env.example      # env config (.env gitignored; never read/commit values)
├── .dockerignore, .gitignore, .gitattributes
├── CLAUDE.md, README.md, LICENSE
```

## Directory Purposes

**`backend/app/api/`:** REST routers built by factories. Files: `health.py` (plain `router`), `portfolio.py` (`create_portfolio_router`), `watchlist.py` (`create_watchlist_router`), re-exported in `__init__.py`.

**`backend/app/db/`:** `connection.py` (path, `transaction`, `use`, `init_db`, `DEFAULT_TICKERS`), `repository.py` (per-table functions), `schema.sql` (6 tables, `CREATE TABLE IF NOT EXISTS`).

**`backend/app/market/`:** price pipeline. `seed_prices.py` holds seed prices and per-ticker GBM params.

**`backend/app/portfolio/`:** business logic between routes and repository.

**`backend/app/llm/`:** `prompt.py` builds messages, `client.py` calls LiteLLM and parses, `chat.py` orchestrates, `router.py` exposes `/api/chat` and `/api/chat/history`.

**`backend/tests/`:** subfolders mirror `app/`; per-folder `conftest.py` in root, `db/`, `llm/`.

**`test/`:** self-contained npm project (Playwright 1.64.1) run via `test/docker-compose.test.yml` with `LLM_MOCK=true`, tmpfs DB, healthcheck on `/api/health`, base URL `http://finally-app:8000`.

**`planning/`:** specs; `PLAN.md` is the source of truth. `MARKET_DATA_SUMMARY.md` summarizes the finished market data work.

## Key File Locations

**Entry Points:** `backend/app/main.py`, `Dockerfile`, `scripts/start_mac.sh`, `scripts/start_windows.ps1`
**Configuration:** `backend/pyproject.toml`, `.env.example`, `docker-compose.yml`, `test/playwright.config.ts`
**Core Logic:** `backend/app/portfolio/trading.py`, `backend/app/market/simulator.py`, `backend/app/llm/chat.py`
**Schema:** `backend/app/db/schema.sql`
**Testing:** `backend/tests/`, `test/e2e/`

## Naming Conventions

**Files:** Python `snake_case.py`; tests `test_<module>.py`; E2E specs `NN-name.spec.ts`; scripts `start_<os>.sh|ps1`.
**Directories:** lowercase single words in `backend/app/`.
**Python symbols:** functions `snake_case`, classes `PascalCase`, router factories `create_<name>_router`, background loops `<name>_loop`, constants `UPPER_SNAKE`.
**DOM test ids:** kebab-case, with `-{TICKER}` suffix for per-ticker elements.

## Where to Add New Code

**New REST endpoint:** router factory in `backend/app/api/<name>.py`, export from `backend/app/api/__init__.py`, include in `backend/app/main.py`; logic in `backend/app/portfolio/`; SQL in `backend/app/db/repository.py` and export in `backend/app/db/__init__.py`. Tests in `backend/tests/api/test_routes.py` and the matching folder.
**New table:** add to `backend/app/db/schema.sql` (with `user_id` default `'default'`).
**New market source:** subclass `MarketDataSource` in `backend/app/market/`, wire in `factory.py`.
**Frontend:** recreate `frontend/` (Next.js + TypeScript + Tailwind, `output: 'export'`, outputs `frontend/out/`); calls same-origin `/api/*`.
**E2E:** new `test/e2e/NN-name.spec.ts` using `test/e2e/helpers.ts`.

## Special Directories

**`backend/static/`:** frontend build output; generated in Docker, gitignored, not committed.
**`db/`:** runtime SQLite; volume `finally-data` mounted at `/app/db` in containers; `DB_PATH` set in Docker.
**`.claude/`:** GSD tooling, partly untracked.
**`planning/archive/`:** historical market data design/review docs.

---

*Structure analysis: 2026-10-19*
