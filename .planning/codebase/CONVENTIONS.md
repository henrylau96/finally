# Coding Conventions

**Analysis Date:** 2026-10-19

Scope: backend (`backend/app/`), scripts (`scripts/`), E2E (`test/`). `frontend/` is absent (deleted in commit 4619f5b for rebuild); no frontend conventions exist yet beyond those in `planning/PLAN.md` (TypeScript, Tailwind, Next.js static export).

## Project-Level Rules (from CLAUDE.md files)

- Python tooling is `uv` only: `uv run ...`, `uv add ...`, `uv sync --extra dev`. Never `python3 x` or `pip install`. uv lives at `~/.local/bin/uv`.
- No emojis in code, prints, or logging.
- Short modules, short functions, clear names. Concise docstrings; sparse comments outside docstrings.
- Do not over-engineer or program defensively; use exceptions where needed.
- Keep `README.md` concise.

## Naming Patterns

**Files:** `snake_case.py`, one concern per module (`backend/app/market/seed_prices.py`, `backend/app/portfolio/trading.py`). Tests are `test_<topic>.py`. E2E specs are numbered `NN-topic.spec.ts` (`test/e2e/03-trading.spec.ts`).

**Functions:** `snake_case`; private helpers prefixed `_` (`_buy`, `_sell`, `_position_view` in `backend/app/portfolio/trading.py`). Router factories are `create_<name>_router(...)` (`create_portfolio_router`, `create_chat_router`, `create_stream_router`). Source factory is `create_market_data_source`.

**Variables/constants:** `snake_case`; module constants `UPPER_SNAKE` (`EPSILON`, `MODEL`, `FALLBACK_MESSAGE`, `DEFAULT_TICKERS`).

**Classes:** `PascalCase`; exceptions end in `Error` (`TradeError`); request models end in `Request` (`TradeRequest`, `ChatRequest`).

**Data identifiers:** tickers uppercased and stripped on entry; sides lowercased. Default user is the string `"default"` passed as `user_id: str = "default"`.

**TypeScript (test/):** camelCase functions (`openApp`, `apiTrade`, `uiTrade`), `data-testid` selectors in kebab-case (`cash-balance`, `position-row-AAPL`, `trade-error`, `buy-button`). The rebuilt frontend must expose these test ids.

## Code Style

**Formatting/Linting:** ruff configured in `backend/pyproject.toml`: line length 100, target py312, rules `E, F, I, N, W`, `E501` ignored. `uv run ruff check app/ tests/` currently passes clean. Imports sorted by ruff `I`.

**Python version:** `requires-python >=3.12`; `backend/.python-version` pins the dev interpreter (Python 3.14 per project notes).

**Typing:** modern syntax (`str | None`, `list[dict]`), `from __future__ import annotations` in most `app/` modules. Pydantic v2 (`BaseModel`, `Field`, `model_validate_json`) for API and LLM schemas.

## Import Organization

1. `from __future__ import annotations` (where used)
2. Stdlib
3. Third party (`fastapi`, `pydantic`, `numpy`)
4. First party absolute `from app import db` / `from app.market import PriceCache`; inside `app/market/` use relative imports (`from .cache import PriceCache`).

Packages re-export their public API from `__init__.py` with `__all__` (`backend/app/db/__init__.py`, `backend/app/market/__init__.py`, `backend/app/api/__init__.py`). Consumers import from the package, e.g. `from app.portfolio import TradeError, execute_trade`. Modules call DB functions via the namespace: `db.get_cash(...)`.

Heavy imports are deferred inside functions (`from litellm import acompletion` in `backend/app/llm/client.py`).

## Error Handling

- Domain failures raise a dedicated exception with a user-facing message: `TradeError` (`backend/app/portfolio/trading.py`). Validate inputs up front, before opening a transaction.
- API layer converts domain errors to HTTP: `except TradeError as e: raise HTTPException(status_code=400, detail=str(e))` (`backend/app/api/portfolio.py`).
- Chat flow reports failed trades inline as `{"status": "failed", "error": ...}` rather than raising (`backend/app/llm/chat.py`).
- LLM output parsing falls back to a friendly message with no actions on `ValidationError`, logging a warning (`parse_response` in `backend/app/llm/client.py`).
- Multi-write operations use `with db.transaction() as conn:` and pass `conn=conn` to repository calls so everything commits or rolls back together.
- Float comparisons on cash/quantity use `EPSILON = 1e-9` tolerance.

## Logging

`logger = logging.getLogger(__name__)` per module; `logger.warning("...%r", value)` with lazy %-formatting. No print in `app/` (only `backend/market_data_demo.py`, which uses `rich`).

## Comments

Module docstring on every module (one line). Public functions/classes get a one-line imperative docstring (`"""Execute a market order at the current cached price and return the trade row."""`). Math-heavy classes get an extended docstring (`GBMSimulator` in `backend/app/market/simulator.py`). Private helpers may omit docstrings.

## Function Design

- Small functions; helpers split out (`_buy`/`_sell`).
- Repository functions take `(..., user_id="default", conn=None)` and use `with use(conn) as c:` from `backend/app/db/connection.py`, so they work standalone or inside a transaction.
- Return plain `dict`/`list[dict]` from services and repositories, rounded for display (`round(x, 2)`).
- Routers are built by factory functions closing over dependencies (`price_cache`, `market_source`) instead of global state; sync `def` endpoints for DB work, `async def` where awaiting (chat).

## Module Design

- Layering: `api/` and `llm/router.py` (HTTP) -> `portfolio/` and `llm/chat.py` (logic) -> `db/` and `market/` (infrastructure). See `backend/app/`.
- Abstract interface `MarketDataSource` (`backend/app/market/interface.py`) with `SimulatorDataSource` and `MassiveDataSource` implementations.
- Config via environment variables read at call time (`DB_PATH`, `LLM_MOCK`, `MASSIVE_API_KEY`), which makes monkeypatching in tests trivial.

## Scripts

Bash: `#!/usr/bin/env bash`, `set -euo pipefail`, `cd "$(dirname "$0")/.."`, idempotent (`docker rm -f ... || true`), overridable `DOCKER` var (`scripts/start_mac.sh`). PowerShell equivalents in `scripts/*.ps1`.

---

*Convention analysis: 2026-10-19*
