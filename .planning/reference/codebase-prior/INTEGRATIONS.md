# External Integrations

**Analysis Date:** 2026-10-19

## APIs & External Services

**LLM (chat assistant):**
- OpenRouter -> Cerebras provider, model `openrouter/openai/gpt-oss-120b`
  - SDK/Client: `litellm` `acompletion`, structured output via `response_format=ChatResponse` (`backend/app/llm/client.py`)
  - Provider pinned with `extra_body={"provider": {"order": ["cerebras"]}}`, `reasoning_effort="low"`
  - Auth: `OPENROUTER_API_KEY` (read by litellm from environment)
  - Mock: `LLM_MOCK=true` uses `backend/app/llm/mock.py` (checked in `backend/app/llm/chat.py`)
  - Project skill: `.claude/skills/cerebras/SKILL.md`

**Market data:**
- Massive (Polygon.io) REST - optional real prices
  - SDK/Client: `massive.RESTClient` (`backend/app/market/massive_client.py`); polls `get_snapshot_all`, falls back to grouped daily bars (`get_grouped_daily_aggs`) for end-of-day tier
  - Auth: `MASSIVE_API_KEY`; poll interval `MASSIVE_POLL_INTERVAL` (default 15s)
  - Selection: `backend/app/market/factory.py`; default is in-process GBM simulator (`backend/app/market/simulator.py`)
  - Docs: `planning/MASSIVE_API.md`

## Data Storage

**Databases:**
- SQLite, single file `db/finally.db`
  - Connection: `DB_PATH` env (default `<repo>/db/finally.db`)
  - Client: stdlib `sqlite3`, raw SQL in `backend/app/db/repository.py`; lazy init via `db.init_db()` in `backend/app/db/connection.py`

**File Storage:**
- Local filesystem only (DB file; static frontend under `backend/static`)

**Caching:**
- In-memory `PriceCache` (`backend/app/market/cache.py`), thread-locked

## Authentication & Identity

**Auth Provider:**
- None. Single user, hardcoded `user_id="default"`.

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- stdlib `logging` per module

## CI/CD & Deployment

**Hosting:**
- Docker container, port 8000 (`Dockerfile`, `docker-compose.yml`); optional cloud (App Runner/Render) not implemented

**CI Pipeline:**
- GitHub Actions: `.github/workflows/claude.yml` (@claude mentions) and `.github/workflows/claude-code-review.yml` (PR review), both `anthropics/claude-code-action@v1` with secret `CLAUDE_CODE_OAUTH_TOKEN`. No test/build workflow.
- E2E: `test/docker-compose.test.yml` runs app (`LLM_MOCK=true`, tmpfs DB, `/api/health` healthcheck) plus `mcr.microsoft.com/playwright:v1.64.1-noble`

## Environment Configuration

**Required env vars:**
- `OPENROUTER_API_KEY` (unless `LLM_MOCK=true`)
- Optional: `MASSIVE_API_KEY`, `MASSIVE_POLL_INTERVAL`, `LLM_MOCK`, `DB_PATH`, `STATIC_DIR`

**Secrets location:**
- Root `.env` (gitignored, passed with `--env-file`); GitHub repo secret for Claude Code action

## Webhooks & Callbacks

**Incoming:**
- None (GitHub workflow triggers only)

**Outgoing:**
- None

## Internal Endpoints (for reference)

- `GET /api/health` (`backend/app/api/health.py`), `GET /api/stream/prices` SSE (`backend/app/market/stream.py`), portfolio (`backend/app/api/portfolio.py`), watchlist (`backend/app/api/watchlist.py`), `POST /api/chat` (`backend/app/llm/router.py`)

---

*Integration audit: 2026-10-19*
