# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-10-20
**Phases:** 6 | **Plans:** 34 | **Commits:** 203 over 2 days

### What Was Built
- Correlated GBM simulator and optional Massive (Polygon) source behind one interface, streaming over SSE to a dark Next.js terminal
- SQLite-backed watchlist, market-order trading, positions, P&L heatmap and portfolio value chart
- FinAlly AI copilot (LiteLLM -> OpenRouter/Cerebras, structured outputs) that trades and edits the watchlist through the same services as the UI
- One-command Docker packaging with a persistent volume, start/stop scripts, tablet layout
- Test suites: 188 pytest, 45 Vitest, 23 Playwright E2E

### What Worked
- **Vertical MVP slices.** Every phase ended with something visible in the browser, and every phase closed with a human-verified gate plan.
- **Goal-backward verification.** All six phases passed first time (scores 3/3 to 6/6), and the milestone audit found 66/66 requirements and 8/8 E2E flows.
- **Shared, lock-owning services.** One code path made chat actions and manual trades behave identically. The integration check found no cross-phase wiring gaps.
- **Root-cause-first debugging** (user rule). Phase 6 recorded probe evidence for the flaky test, and the review fixer refused to "fix" WR-05 without proof.
- **The post-phase code review caught a real critical bug.** The EOD throttle counted only history calls against the 5/min free tier. All unit tests and the user's UAT had missed it.

### What Was Inefficient
- **UAT on real Massive EOD data surfaced gaps late.** Empty main chart and empty sparklines needed four gap-closure plans (06-06/07/09/10) and a second gate (06-08). The EOD data shape (one timestamp per day) was not exercised by simulator-based E2E.
- **WSL/Windows tool split:**
  - gsd-sdk runs on Windows node, so it could not read `/tmp` manifests or follow WSL worktree gitfiles, and worktree merges had to be done by hand with WSL git.
  - The Playwright wrapper silently dropped `BASE_URL` without `WSLENV`.
- **Review fixes landed after the E2E gate,** so the full Playwright suite needed a separate pre-milestone rerun (quick task 261020-nml).
- **SUMMARY frontmatter was inconsistent** (missing `requirements-completed`, one-liners missing or garbled). That forced manual requirement cross-checks and a hand-written MILESTONES.md.

### Patterns Established
- Phase gate plan at the end of every phase: suites + curl smoke + restart persistence + E2E + human browser check.
- `LLM_MOCK=true` and blanked `MASSIVE_API_KEY` in every automated test path; real keys only via `--env-file`.
- Test scripts use their own containers, volumes and ports, and refuse the real `finally` / `finally-data` names.
- One rate limiter wraps every external API call (not per-endpoint throttles).

### Key Lessons
1. When an optional real data source exists, add at least one E2E or contract test that uses its data shape (for example, EOD bars with identical timestamps). Simulator-only E2E hides shape-dependent bugs.
2. Run the code review before the final human gate, or rerun the E2E suite after review fixes. Otherwise the gate's evidence goes stale.
3. Rate limits must count every call to the provider, not just the endpoint being worked on.
4. In a WSL + Windows-tool setup, keep agent scratch files and worktrees under `/mnt/c`, and pass env vars through `WSLENV`.
5. Executors should always write SUMMARY frontmatter `one-liner` and `requirements-completed`. Milestone tooling depends on them.

### Cost Observations
- Model mix: orchestration on Opus; executors, verifiers, reviewers and auditors on Sonnet; planners on Opus (balanced profile)
- Notable: parallel worktree waves saved wall-clock time, but each manual merge in WSL cost orchestration time

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 6 | 34 | From-scratch GSD rebuild with vertical slices and per-phase human gates |

### Cumulative Quality

| Milestone | Backend tests | Frontend tests | E2E tests |
|-----------|---------------|----------------|-----------|
| v1.0 | 188 | 45 | 23 |

### Top Lessons (Verified Across Milestones)

1. (To be confirmed by later milestones) Exercise every real data source's shape in automated tests, not just the default simulator.
