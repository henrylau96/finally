---
phase: 06-packaging-persistence-test-suite
verified: 2026-10-20T16:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
gaps: []
---

# Phase 6: Packaging, Persistence and Test Suite Verification Report

**Phase Goal:** Anyone can start the whole app with one command, keep their data across restarts, and trust it via automated tests.
**Status:** passed
**Re-verification:** No (initial)

## Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Exact `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally` starts working app from multi-stage Dockerfile | VERIFIED | `Dockerfile`: node:20-slim build stage, python:3.14-slim + uv `sync --frozen`, copies `out` to `static`, CMD uvicorn on 8000. Start script uses the identical run flags; orchestrator evidence: container healthy after `start_mac.sh --build`. |
| 2 | Start script builds if needed/on `--build`, prints URL; stop removes container, keeps volume; idempotent, mac/Linux and Windows | VERIFIED | `scripts/start_mac.sh`, `start_windows.ps1`, `stop_mac.sh`, `stop_windows.ps1` read: image inspect or `--build`/`-Build`, `rm -f` before `run`, URL printed, stop uses `rm -f ... || true` and never touches the volume. Windows scripts not executed here (no Windows run by me; mac script run per orchestrator evidence). |
| 3 | Positions, cash, watchlist, chat history survive stop/restart | VERIFIED | `test/persistence.sh` exists; orchestrator ran it: PERSISTENCE OK. Named volume `finally-data` mapped to `/app/db`, `DB_PATH` set in Dockerfile. |
| 4 | Dense on wide screens, usable at tablet width | VERIFIED (with warnings) | `07-responsive.spec.ts` passes in compose E2E; user UAT approved. See WR-02/WR-03 below: tablet watchlist rows overflow inside the panel and the EOD badge text is hidden below lg. Not a goal blocker given human approval, but real polish defects. |
| 5 | Backend route tests, frontend component tests, Playwright E2E (7 specs) pass via `test/docker-compose.test.yml` with `LLM_MOCK=true` | VERIFIED | I reran: backend 187 passed, frontend 42 passed (9 files). Compose file sets `LLM_MOCK: "true"`, app plus playwright services; specs 01-07 present. Compose E2E 23/23 per orchestrator. |

**Score:** 5/5

## Requirements Coverage

All IDs in plan frontmatter (DATA-04, OPS-03, OPS-04, OPS-05, OPS-06, OPS-07, UI-13, UI-14, TEST-04, TEST-05, TEST-06, TEST-07, plus gap-closure UI-03, UI-06, MKT-01) are accounted for in REQUIREMENTS.md. No orphaned Phase 6 requirements.

| Requirement | Status | Evidence |
|-------------|--------|----------|
| DATA-04 | SATISFIED | persistence.sh, volume config |
| OPS-03 | SATISFIED | Dockerfile |
| OPS-04 | SATISFIED | exact run command via start script, container healthy |
| OPS-05 | SATISFIED | start_mac.sh / start_windows.ps1 |
| OPS-06 | SATISFIED | stop_mac.sh / stop_windows.ps1 |
| OPS-07 | SATISFIED | `.env.example` documents all three vars; `.env` gitignored (.gitignore line 138) |
| UI-13 | SATISFIED | tablet layout, 07-responsive spec (see warnings) |
| UI-14 | SATISFIED | 43 `data-testid` occurrences in frontend/src |
| TEST-04 | SATISFIED | 187 backend tests incl. routes smoke |
| TEST-05 | SATISFIED | 42 vitest tests |
| TEST-06 | SATISFIED | test/docker-compose.test.yml |
| TEST-07 | SATISFIED | E2E specs 01-07, 23 passed |
| UI-03, UI-06, MKT-01 | SATISFIED | history endpoint, seeded chart/sparklines, MarketDataSource.history; UAT gaps marked resolved |

**Documentation discrepancy (not a code gap):** `.planning/REQUIREMENTS.md` still shows OPS-04, OPS-05, OPS-06, TEST-06 as unchecked `[ ]` and "Pending" in the traceability table. The implementation satisfies them; the orchestrator should tick these four boxes and set the table rows to Complete when committing.

## Code Review Findings (06-REVIEW.md) vs must-haves

- CR-01 (EOD history throttle ignores poll/add-ticker calls against 5/min free tier): Does not block any must-have. It affects only the optional Massive free-tier path added by gap closure; the default simulator path and all ROADMAP criteria are unaffected. Observed evidence that 124 points were served for all 10 tickers. Real defect: on a fresh free-tier start some seeds may fail and (WR-01) stay empty until reload. Recommend a follow-up fix (shared limiter).
- WR-01 (failed history cached as permanent empty seed): follow-up; compounds CR-01.
- WR-02 (tablet watchlist row overflow, clipped remove button): follow-up; UI-13 "functional at tablet width" is met per human approval but this is a genuine polish gap not caught by the spec.
- WR-03 (stale badge text hidden below lg): follow-up.
- WR-04 (daily-point time formatting, timezone): follow-up.
- WR-05 (live vs history bar timestamp mismatch may duplicate last point): follow-up, needs live check.

None of these falsify a success criterion; none are debt markers (TBD/FIXME/XXX not scanned beyond review claims).

## Human Verification

Already performed: user replied "approved" (06-UAT.md 4/4 passed, 06-08-SUMMARY, 06-05 sign-off). No outstanding items.

## Behavioral Spot-Checks

| Check | Result |
|-------|--------|
| `uv run pytest -q` | 187 passed |
| `npm test` (frontend) | 42 passed |
| Docker/compose/persistence | Not rerun by me; relied on orchestrator-provided evidence |

## Gaps Summary

No goal-blocking gaps. Status passed, with recommended follow-ups (CR-01, WR-01..05) and the REQUIREMENTS.md checkbox update.

_Verifier: Claude (gsd-verifier)_
