---
phase: quick-261020-nml
plan: 01
status: complete
requirements: [IN-05]
commits: [7be4ee3]
---

# Quick 261020-nml: Persistence guard and pre-milestone check

## Task 1
`test/persistence.sh` now exits 2 with a `Refusing:` message, before the EXIT trap and any Docker call, when `VOLUME=finally-data` or `CONTAINER=finally`. Verified with a bogus `DOCKER` command (never reached). Commit 7be4ee3.

## Task 2 (evidence)
- Compose E2E on HEAD: exit 0, 23 passed, 0 failed (specs 01:3, 02:2, 03:5, 04:1, 05:7, 06:1, 07:4). `down -v` run afterwards; `ps -a` empty.
- `scripts/start_mac.sh --build`: `finally` container running rebuilt image on 8000; health `{"status":"ok","source":"massive"}`.
- `bash test/persistence.sh`: PERSISTENCE OK.
- `finally-data` volume present.

## Deviations
None.
