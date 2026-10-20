---
phase: quick-261020-nml
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - test/persistence.sh
autonomous: true
requirements: [IN-05]

must_haves:
  truths:
    - "test/persistence.sh exits non-zero with a clear message, before any Docker call, when VOLUME=finally-data or CONTAINER=finally"
    - "The default persistence run (finally-p / finally-test-data / port 8001) is unchanged"
    - "Compose Playwright E2E (specs 01-07) passes on an image built from current HEAD"
    - "The user's finally container runs the rebuilt image on port 8000 with the finally-data volume intact"
  artifacts:
    - path: "test/persistence.sh"
      provides: "Guard refusing the real volume and container names"
      contains: "finally-data"
  key_links:
    - from: "test/persistence.sh guard"
      to: "trap cleanup EXIT"
      via: "guard placed before the trap and the first cleanup call"
      pattern: "Refusing"
---

<objective>
Pre-milestone safety and regression check.

Purpose: Close the data-loss part of review finding IN-05 (persistence.sh deletes `$VOLUME`, so `VOLUME=finally-data` would wipe user data), then prove the Phase 6 review fixes hold by rerunning the full compose E2E suite on current HEAD, and leave the user's app running on the new image.
Output: Guarded test/persistence.sh, E2E evidence in the SUMMARY, rebuilt `finally` container.
</objective>

<execution_context>
@C:/Users/fulai/projects/finally/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/fulai/projects/finally/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@test/persistence.sh
@test/docker-compose.test.yml
@scripts/start_mac.sh

Environment rules: WSL. docker/npm/npx are wrappers calling Windows binaries, so run every command from /mnt/c/Users/fulai/projects/finally. Use `uv run`, never python3. The repo .env holds real keys: never print it (no `cat .env`, no `env`, no echo of values). Port 8000 is held by the user's `finally` container; the `finally-data` volume must survive every step; never run `docker volume rm finally-data`. The executor runs on the main working tree: stage explicit paths only (never `.claude/`). Last compose E2E run before the review fixes: 23 passed.

Current persistence.sh structure (lines 7-19): variables DOCKER, IMAGE, CONTAINER (default finally-p), VOLUME (default finally-test-data), PORT, URL are assigned; then `cleanup()` (docker rm -f container, docker volume rm volume) is defined; then `trap cleanup EXIT` and an immediate `cleanup` call. The guard must sit before `trap cleanup EXIT`, otherwise the EXIT trap would still delete the volume.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Guard persistence.sh against the real volume and container names</name>
  <files>test/persistence.sh</files>
  <action>Per review IN-05 (data-loss part only), add a minimal guard right after the `URL=` assignment and before `cleanup()` / `trap cleanup EXIT`: if `$VOLUME` equals `finally-data` or `$CONTAINER` equals `finally`, print to stderr a single line starting with `Refusing:` that says these are the user's real app volume/container and would be deleted, then `exit 2`. Two to four lines of plain bash (one `if` with `||`, or two one-line tests), no functions or extra flags. Also update the header comment to mention the refusal in a few words. Do not change anything else in the script (the other IN-05 points are out of scope for this quick task).</action>
  <verify>
    <automated>cd /mnt/c/Users/fulai/projects/finally && bash -n test/persistence.sh && for V in "VOLUME=finally-data" "CONTAINER=finally"; do OUT=$(env $V DOCKER=no-such-docker-cmd bash test/persistence.sh 2>&1); RC=$?; test $RC -ne 0 && echo "$OUT" | grep -q '^Refusing' && ! echo "$OUT" | grep -q 'no-such-docker-cmd' || { echo "guard failed for $V"; exit 1; }; done && docker volume ls -q | grep -qx finally-data && echo guard-ok</automated>
  </verify>
  <done>Both overrides exit non-zero with a `Refusing:` line and never invoke Docker (the bogus DOCKER command is never reached); finally-data volume still present; script otherwise unchanged. Commit `test/persistence.sh` only: `fix(quick-261020-nml): refuse real finally volume/container in persistence.sh`.</done>
</task>

<task type="auto">
  <name>Task 2: Compose E2E on current HEAD, persistence run, restart the user's app</name>
  <files>(no source changes; runs test/docker-compose.test.yml, test/persistence.sh, scripts/start_mac.sh)</files>
  <action>(1) From /mnt/c/Users/fulai/projects/finally run `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright`, capture its exit code, and ALWAYS run `docker compose -f test/docker-compose.test.yml down -v` afterwards regardless of result. Record per-spec pass/fail counts for specs 01-07 and the total (expect at least 23 passed, 0 failed). If anything fails, stop, record the failing test and its error, and do not apply fixes (report root cause evidence in the SUMMARY instead). (2) Check port 8000 is held only by the `finally` container or is free (`docker ps --filter publish=8000`); if something else holds it, stop and report. Then run `bash scripts/start_mac.sh --build` so the user's app runs an image built from current HEAD with the finally-data volume and the real .env. Wait up to 60 s for `curl -s localhost:8000/api/health` to report status ok and record its `source`. (3) Run `bash test/persistence.sh` with default variables (its own finally-p container, finally-test-data volume, port 8001; it runs the `finally` image tag just rebuilt in step 2) and confirm it prints PERSISTENCE OK. Record all evidence (exit codes, spec counts, health output, `docker volume ls -q | grep -x finally-data`) in the SUMMARY.</action>
  <verify>
    <automated>cd /mnt/c/Users/fulai/projects/finally && docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright; R=$?; docker compose -f test/docker-compose.test.yml down -v; test $R -eq 0 && bash scripts/start_mac.sh --build && for i in $(seq 60); do curl -s localhost:8000/api/health | grep -q '"status":"ok"' && break; sleep 1; done && bash test/persistence.sh | grep -q 'PERSISTENCE OK' && docker volume ls -q | grep -qx finally-data && curl -s localhost:8000/api/health | grep -q '"status":"ok"' && echo premilestone-ok</automated>
  </verify>
  <done>Compose E2E exits 0 with specs 01-07 all passing and `docker compose -f test/docker-compose.test.yml ps -a` empty afterwards; PERSISTENCE OK printed; `finally` container running the freshly built image on port 8000; `finally-data` volume present; health reports ok. No source changes, so nothing to commit beyond the SUMMARY.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test script -> user data volume | persistence.sh deletes whatever `$VOLUME` names on exit |
| host .env -> container | real API keys passed via `--env-file` by start_mac.sh |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-q261020-01 | Tampering / DoS | test/persistence.sh cleanup | mitigate | guard refuses VOLUME=finally-data and CONTAINER=finally before the EXIT trap is installed; verified with a bogus DOCKER command |
| T-q261020-02 | Information disclosure | .env keys | mitigate | never cat/echo .env or env; compose E2E keeps `MASSIVE_API_KEY: ""` and `LLM_MOCK: "true"` |
| T-q261020-03 | DoS | finally-data volume during rebuild | mitigate | only `docker rm -f` on containers and `down -v` on the test compose project (tmpfs, no named volumes); volume presence asserted in verify |
</threat_model>

<verification>
- Guard check (Task 1 automated) prints guard-ok
- Full gate (Task 2 automated) prints premilestone-ok
- `git status` shows only test/persistence.sh and the quick-task SUMMARY staged; `.claude/` untouched
</verification>

<success_criteria>
- persistence.sh can no longer delete the user's real volume or container
- Compose E2E 01-07 passes on current HEAD (at least 23 passed, 0 failed)
- User's app is running the rebuilt image at http://localhost:8000 with data preserved
</success_criteria>

<output>
Create `.planning/quick/261020-nml-pre-milestone-check-persistence-guard-an/261020-nml-SUMMARY.md` when done
</output>
