# Technology Stack

**Analysis Date:** 2026-10-19

> The `frontend/` directory is absent (deleted in commit 4619f5b so it can be rebuilt). The `Dockerfile` still references it, so the image does not build until `frontend/` is restored. Frontend stack below is from the spec in `planning/PLAN.md`, not from code.

## Languages

**Primary:**
- Python >=3.12 (`backend/pyproject.toml`); Docker image uses 3.14-slim - backend, all server logic in `backend/app/`

**Secondary:**
- TypeScript - Playwright E2E tests in `test/e2e/*.spec.ts`; planned Next.js frontend (absent)
- Bash / PowerShell - `scripts/*.sh`, `scripts/*.ps1`

## Runtime

**Environment:**
- CPython (uvicorn ASGI server), single process, asyncio background tasks
- Node 20 slim (Docker build stage for frontend only); Node needed locally for `test/`

**Package Manager:**
- uv (backend) - lockfile `backend/uv.lock` present
- npm (`test/package-lock.json` present)

## Frameworks

**Core:**
- FastAPI (locked 0.128.7) - REST + SSE API, serves static files (`backend/app/main.py`)
- uvicorn[standard] (locked 0.40.0) - ASGI server
- Pydantic (locked 2.12.5) - request models and LLM structured output schema (`backend/app/llm/schema.py`)
- Next.js static export (planned, `frontend/` absent)

**Testing:**
- pytest (9.0.2) + pytest-asyncio (`asyncio_mode = "auto"`) + pytest-cov + httpx - `backend/tests/`
- Playwright 1.64.1 - E2E in `test/e2e/`

**Build/Dev:**
- hatchling build backend (`backend/pyproject.toml`)
- ruff (0.15.0) - lint, line-length 100, rules E,F,I,N,W, target py312
- Docker multi-stage build (`Dockerfile`)

## Key Dependencies

**Critical:**
- litellm (1.106.0) - LLM calls via OpenRouter (`backend/app/llm/client.py`)
- massive (2.2.0) - Massive/Polygon REST client (`backend/app/market/massive_client.py`)
- numpy (2.4.2) - GBM simulator math (`backend/app/market/simulator.py`)
- python-dotenv (1.2.4) - loads root `.env` (`backend/app/main.py`)

**Infrastructure:**
- sqlite3 (stdlib) - persistence (`backend/app/db/connection.py`)
- rich - used by `backend/market_data_demo.py`

## Configuration

**Environment:**
- `.env` at repo root (present, gitignored; never read), template `.env.example`
- Vars: `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `MASSIVE_POLL_INTERVAL`, `LLM_MOCK`
- Container-only vars set in `Dockerfile`: `DB_PATH` (default `<repo>/db/finally.db`), `STATIC_DIR` (default `backend/static`)

**Build:**
- `backend/pyproject.toml`, `backend/uv.lock`
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- `test/playwright.config.ts`, `test/docker-compose.test.yml`

## Platform Requirements

**Development:**
- uv, Python 3.12+; run backend from `backend/` (`uv run uvicorn app.main:app`), tests `uv run pytest`
- Docker for the full image and E2E; Node/npm for `test/`

**Production:**
- Single Docker container, port 8000, named volume `finally-data` mounted at `/app/db`
- Start/stop via `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`

---

*Stack analysis: 2026-10-19*
