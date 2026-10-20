---
phase: 06-packaging-persistence-test-suite
plan: 04
subsystem: infra
tags: [docker, persistence, sqlite, volume, secrets]
requires: []
provides:
  - test/persistence.sh restart-persistence proof (DATA-04)
affects: [06-05]
tech-stack:
  added: []
  patterns: [throwaway container/volume/port for destructive checks]
key-files:
  created: [test/persistence.sh]
  modified: [test/README.md]
key-decisions:
  - "Persistence check uses its own container finally-p, volume finally-test-data, port 8001, no --env-file"
requirements-completed: [DATA-04, OPS-07, OPS-03]
duration: 10min
completed: 2026-10-20
---

# Phase 6 Plan 04: Persistence Check Summary

Self-cleaning `test/persistence.sh` proves cash, positions, watchlist and chat history survive container removal on a named volume; multi-stage image builds and env hygiene is confirmed.

## Evidence
- `docker build -t finally .` succeeded (multi-stage Node -> Python).
- `bash test/persistence.sh` printed `PERSISTENCE OK`. Before and after were identical: cash 9620.0, AAPL 2 @ 190.0, PYPL in watchlist, 2 chat message ids.
- No leftover `finally-p` container or `finally-test-data` volume; user `finally` container and `finally-data` volume untouched.
- `.env.example` has OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK; `.env` is gitignored and listed in .dockerignore; no `.env` in /app or /app/backend of the image. `load_dotenv` on a missing file is a no-op, so env comes from `--env-file` at run time.

## Deviations from Plan
None. Note: the user's running `finally` container still uses the old image; the `finally` tag now points to the new build.

## Commits
- b9e98df: test(06-04): add container restart persistence check

## Self-Check: PASSED
