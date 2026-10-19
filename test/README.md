# FinAlly E2E Tests

Playwright tests (`e2e/`) run against the app at `BASE_URL` (default `http://localhost:8000`).
The app must run with `LLM_MOCK=true`. Specs share one app state and run serially; the
fresh-start spec expects a fresh database ($10,000 cash, default watchlist).

## Run in Docker (recommended)

From the repo root:

```bash
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
docker compose -f test/docker-compose.test.yml down -v
```

The app uses a throwaway tmpfs database, so every run starts fresh.

## Run locally

Start the app with a fresh database, then run the suite:

```bash
cd backend && LLM_MOCK=true DB_PATH=/tmp/finally-e2e.db uv run uvicorn app.main:app --port 8000
cd test && npm install && npx playwright install chromium && npx playwright test
```

Reports: `npx playwright show-report`; failure traces are in `test-results/`.
