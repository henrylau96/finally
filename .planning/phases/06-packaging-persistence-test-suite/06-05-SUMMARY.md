# Phase 6 Plan 05: Phase Gate Summary (awaiting human sign-off)

Automated gate evidence for Phase 6 on the final image; Task 3 (human verification) is pending.

## Task 1: suites and compose E2E
- Backend pytest: 173 passed. Frontend: vitest 24 passed (6 files), lint, typecheck, build clean.
- Compose E2E (`--exit-code-from playwright`): first run 18 passed / 5 failed (05-chat); after fix 23 passed, exit 0, `ps -a` empty.

| TEST-07 scenario | Spec | Result |
|---|---|---|
| Fresh start (watchlist, $10k, streaming) | 01-fresh-start | 3/3 |
| Add/remove ticker | 02-watchlist | 2/2 |
| Buy and sell | 03-trading | 5/5 |
| Heatmap and P&L chart | 04-portfolio-viz | 1/1 |
| Mocked AI chat trade inline | 05-chat | 7/7 |
| SSE reconnect | 06-sse-reconnect | 1/1 |
| Responsive (1600/1280/1024/768) | 07-responsive | 4/4 |

## Deviation
**[Rule 1 - Bug] Chat crashed on non-secure origins.** Playwright failure screenshot showed Next's "This page couldn't load" right after sending a chat message. Cause: `crypto.randomUUID()` in `frontend/src/lib/useChat.ts` `localEntry` is undefined outside secure contexts; compose reaches the app at `http://finally-app:8000`. Fix: local counter ids. File: `frontend/src/lib/useChat.ts`. Commit 1d93739. Frontend tests/lint/typecheck and full E2E rerun green.

## Task 2: image, persistence, scripts (all evidenced)
- Port 8000 was held by the `finally` container only. `stop_mac.sh` x2: rc 0 both, volume kept.
- Exact `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally` (+ `-d --name finally-oc`): `/api/health` `{"status":"ok","source":"massive"}`, HTML contains "FinAlly", SSE `data:` received; container removed.
- `test/persistence.sh`: PERSISTENCE OK.
- `start_mac.sh` x2 (no build) + `--build` (rebuilt): each printed "FinAlly is running at http://localhost:8000", one `finally` container, health ok after startup (health took longer than 6 s on the first two; waited in later checks). `stop_mac.sh` x2: container gone, volume kept.
- `start_windows.ps1 -NoBrowser` x2 + `-Build -NoBrowser` via powershell.exe: URL printed, health ok, one container; the `-Build` run showed docker build output. `stop_windows.ps1` x2: rc 0, container gone, volume kept.
- Final state: `finally` running on new image via `start_mac.sh`, health ok, volume present ("gate-ops-ok").

## Task 3: pending user approval (layout at 1920/1024/768 and persistence after stop/start).

Duration: ~10 min. Requirements: OPS-03..06, TEST-06, TEST-07, DATA-04, UI-13 (sign-off pending).
