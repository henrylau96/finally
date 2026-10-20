---
phase: 06
slug: packaging-persistence-test-suite
status: verified
threats_open: 0
asvs_level: 1
created: 2026-10-20
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| host .env -> container | Real API keys passed at run time via `--env-file` | OPENROUTER / MASSIVE API keys (secret) |
| gate scripts -> user data volume | Start/stop scripts and persistence test touch Docker volumes | User portfolio, trades, chat (SQLite) |
| browser -> /api/history/{ticker} | Path parameter from watchlist selection | Ticker symbol (untrusted input) |
| backend -> Massive API | Polls, add-ticker quotes and daily history on a rate-limited free tier | Market data, API quota |
| npm registry -> build stage | Test toolchain installed for the frontend build | Third-party packages |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-06-01 | Tampering | local E2E server | mitigate | Port 8061, `mktemp -d` DB_PATH, `MASSIVE_API_KEY=` + `LLM_MOCK=true`, stop by PID (06-01-PLAN.md:75,102,151) | closed |
| T-06-SC | Tampering | npm installs (vitest and peers) | mitigate | Pinned major ranges in frontend/package.json:21-35; lockfiles tracked; no install scripts in the vitest chain | closed |
| T-06-04 | Tampering | production image | mitigate | Test packages in devDependencies; runtime stage copies only `frontend/out` (Dockerfile:22); `uv sync --no-dev` | closed |
| T-06-06 | Tampering | POST /api/chat, /api/portfolio/trade | mitigate | 422 tests: test_routes_smoke.py:11-14, test_portfolio_api.py:60-73 | closed |
| T-06-07 | Information disclosure | test runs | mitigate | conftest.py:7 blanks MASSIVE_API_KEY; autouse `no_network` guard | closed |
| T-06-08 | Repudiation | flaky test | mitigate | Root cause with probe evidence in 06-03-SUMMARY.md:27; tolerance unchanged | closed |
| T-06-09 | Information disclosure | image layers | mitigate | `.env` in .dockerignore:2; keys only via `--env-file` (start_mac.sh:25, start_windows.ps1:21) | closed |
| T-06-10 | Tampering / DoS | user data volume | mitigate | persistence.sh:8-17 uses `finally-p`, `finally-test-data`, port 8001; trap cleans only its own resources | closed |
| T-06-11 | Information disclosure | persistence run | mitigate | persistence.sh:27-28 `-e LLM_MOCK=true -e MASSIVE_API_KEY=`, no `--env-file` | closed |
| T-06-13 | Information disclosure | .env keys | mitigate | docker-compose.test.yml:7-8 `LLM_MOCK: "true"`, `MASSIVE_API_KEY: ""`; no script prints .env | closed |
| T-06-14 | Tampering / DoS | finally-data volume | mitigate | stop_mac.sh:6 / stop_windows.ps1:2 only `docker rm -f finally`; no `volume rm finally-data` | closed |
| T-06-15 | Denial of service | port 8000 | mitigate | Process check recorded in 06-05-SUMMARY.md:23 and 06-08-SUMMARY.md:28 | closed |
| T-06-17 | Tampering | history route path param | mitigate | history.py:15-19 `normalize_ticker` before `source.history`; 422 on invalid | closed |
| T-06-18 | Denial of service | Massive quota | mitigate | Per-ticker per-NY-day cache (massive_source.py:97-107); failures return [] uncached (130-139) | closed |
| T-06-19 | Information disclosure | error logs | mitigate | massive_source.py:133,136 log ticker and BadResponse text only; route never returns upstream bodies | closed |
| T-06-20 | Tampering | useHistory fetch path | mitigate | Server-side ticker validation; non-ok responses ignored (useHistorySeeds.ts:25) | closed |
| T-06-21 | Denial of service | chart data ordering | mitigate | `mergePoints` keeps only live points at/after the last history time (chartPoints.ts:14-20); unit tests in chartPoints.test.ts | closed |
| T-06-23 | Denial of service | Massive quota during gate | mitigate | Sequential history calls through the throttle (06-08-SUMMARY.md) | closed |
| T-06-24 | Denial of service | Massive call quota | mitigate | Post-review (CR-01): all Massive calls go through `_call` with one `_api_lock` and a 5-per-61 s sliding window in EOD mode (massive_source.py:111-117); history single-flight via `_history_lock` + cache re-check (100-106) | closed |
| T-06-26 | Information disclosure | error logs | mitigate | No log call references the API key; massive_parse.py has no logging | closed |
| T-06-27 | Denial of service | useHistorySeeds fan-out | mitigate | Post-review (WR-01): strictly sequential fetches; failed tickers retried by one 60 s timer only when nothing is pending (useHistorySeeds.ts:15-34) | closed |
| T-06-02 | Information disclosure | data-testid attributes | accept | See Accepted Risks Log | closed |
| T-06-03 | Denial of service | ChatDock matchMedia | accept | See Accepted Risks Log | closed |
| T-06-05 | Information disclosure | test fixtures | accept | See Accepted Risks Log | closed |
| T-06-12 | Elevation of privilege | container runs as root | accept | See Accepted Risks Log | closed |
| T-06-16 | Tampering | ghcr.io/astral-sh/uv:latest | accept | See Accepted Risks Log | closed |
| T-06-22 | Information disclosure | chart rendering | accept | See Accepted Risks Log | closed |
| T-06-25 | Denial of service | request queue behind lock | accept | See Accepted Risks Log | closed |
| T-06-28 | Tampering / XSS | Sparkline rendering | accept | See Accepted Risks Log | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-02 | Test hooks expose only values already rendered on screen in a single-user local app | plan 06-01 | 2026-10-20 |
| AR-06-02 | T-06-03 | Single matchMedia read on mount, no user-controlled input | plan 06-01 | 2026-10-20 |
| AR-06-03 | T-06-05 | Mock data only; fetch and chat mocked, no keys | plan 06-02 | 2026-10-20 |
| AR-06-04 | T-06-12 | Local single-user course app; root in container noted only | plan 06-04 | 2026-10-20 |
| AR-06-05 | T-06-16 | Official Astral registry tag (Dockerfile:12); pin deferred | plan 06-05 | 2026-10-20 |
| AR-06-06 | T-06-22 | Numeric points rendered to canvas; no HTML injection path | plan 06-07 | 2026-10-20 |
| AR-06-07 | T-06-25 | Single user; queue bounded by watchlist size; cached tickers bypass the lock | plan 06-09 | 2026-10-20 |
| AR-06-08 | T-06-28 | Numbers only via React SVG attributes, same-origin backend | plan 06-10 | 2026-10-20 |

*Accepted risks do not resurface in future audit runs.*

### Non-blocking observations

- `test/persistence.sh` runs `docker volume rm "$VOLUME"` with `VOLUME` overridable; `VOLUME=finally-data` would delete real user data. Default is safe; a guard refusing `finally-data` would remove the risk (review IN-05).
- Start scripts do not check the port 8000 owner in code; a foreign holder only makes `docker run` fail, no data risk.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-20 | 28 | 28 | 0 | gsd-security-auditor (ASVS L1, block_on high) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-20
