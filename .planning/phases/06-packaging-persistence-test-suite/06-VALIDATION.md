---
phase: 6
slug: packaging-persistence-test-suite
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-20
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 + pytest-asyncio (backend); Vitest + React Testing Library (frontend, Wave 0 install); Playwright 1.64 (E2E) |
| **Config file** | `backend/pyproject.toml`; `frontend/vitest.config.ts` (Wave 0); `test/playwright.config.ts` |
| **Quick run command** | `cd backend && uv run pytest -q -x` / `cd frontend && npm test` |
| **Full suite command** | `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` then `down -v` |
| **Estimated runtime** | ~40s backend, ~10s frontend, ~3-5 min E2E |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (pytest `-x` for backend; `npm test`, `npm run typecheck`, `npm run lint` for frontend)
- **After every plan wave:** Backend full + frontend full + `npm run build`
- **Before `/gsd:verify-work`:** Full compose E2E green + `test/persistence.sh` green + start/stop scripts run twice
- **Max feedback latency:** 60 seconds (quick commands)

---

## Per-Task Verification Map

Filled in by the planner per task. Requirement-to-test mapping:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| OPS-03/04 | image builds; container healthy on :8000 | smoke | `docker build -t finally . && docker run ... && curl /api/health` | ❌ W0 | ⬜ pending |
| OPS-05/06 | start builds/runs/prints URL; stop removes container, keeps volume; repeat-safe | smoke | run each script twice; `docker ps`, `docker volume ls` | ✅ scripts | ⬜ pending |
| OPS-07 | `.env.example` has 3 vars; `.env` ignored | static | `grep` + `git check-ignore .env` | ✅ | ⬜ pending |
| DATA-04 | state survives rm + re-run on same volume | integration | `bash test/persistence.sh` | ❌ W0 | ⬜ pending |
| UI-13 | no horizontal scroll 768-1280; dock collapsed <1280 | e2e | Playwright `07-responsive.spec.ts` | ❌ W0 | ⬜ pending |
| UI-14 | new test hooks present with data attrs | unit + e2e | `npm test` + specs | ❌ W0 | ⬜ pending |
| TEST-04 | route status codes, shapes, errors | integration | `uv run pytest tests -q` | ✅ audit gaps | ⬜ pending |
| TEST-05 | portfolio calc, flash, watchlist CRUD, chat loading | unit | `npm test` | ❌ W0 | ⬜ pending |
| TEST-06 | compose runs app + playwright with LLM_MOCK | e2e infra | full suite command | ✅ | ⬜ pending |
| TEST-07 | 7 scenarios pass | e2e | full suite command | ✅ specs 01-06 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Vitest toolchain installed; `frontend/vitest.config.ts`, `frontend/vitest.setup.ts`, `test` script in `frontend/package.json`
- [ ] `frontend/src/**/*.test.ts(x)` component/unit tests
- [ ] `test/e2e/07-responsive.spec.ts`
- [ ] `test/persistence.sh`
- [ ] Flaky `test_cache_seeded_before_start_returns` reproduced and fixed at root cause

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Windows PowerShell start/stop scripts | OPS-05/06 | May not be runnable from WSL | Run `scripts/start_windows.ps1` twice, then `scripts/stop_windows.ps1` twice; confirm container gone, volume kept |
| Dense layout feel on wide screens | UI-13 | Visual judgement | Open at 1920px and 1024px; confirm no wasted space and dock usable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
