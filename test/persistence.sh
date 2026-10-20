#!/usr/bin/env bash
# Prove data survives a container restart on a named volume. Uses its own
# container, volume and port; never touches the user's finally container.
set -euo pipefail

cd "$(dirname "$0")/.."
DOCKER="${DOCKER:-docker}"
IMAGE="${IMAGE:-finally}"
CONTAINER="${CONTAINER:-finally-p}"
VOLUME="${VOLUME:-finally-test-data}"
PORT="${PORT:-8001}"
URL="http://localhost:$PORT"

cleanup() {
  "$DOCKER" rm -f "$CONTAINER" >/dev/null 2>&1 || true
  "$DOCKER" volume rm "$VOLUME" >/dev/null 2>&1 || true
}
trap cleanup EXIT
cleanup

start() {
  "$DOCKER" run -d --name "$CONTAINER" -v "$VOLUME":/app/db -p "$PORT":8000 \
    -e LLM_MOCK=true -e MASSIVE_API_KEY= "$IMAGE" >/dev/null
  for _ in $(seq 60); do
    curl -sf "$URL/api/health" >/dev/null && return
    sleep 1
  done
  echo "FAIL: app did not become healthy" >&2
  exit 1
}

post() { curl -sf -X POST -H 'Content-Type: application/json' -d "$2" "$URL$1" >/dev/null; }

state() {
  "$DOCKER" exec "$CONTAINER" python -c '
import json, urllib.request
def get(p):
    return json.load(urllib.request.urlopen("http://localhost:8000" + p))
pf = get("/api/portfolio")
print(json.dumps({
    "cash": pf["cash_balance"],
    "positions": sorted([p["ticker"], p["quantity"], p["avg_cost"]] for p in pf["positions"]),
    "watchlist": sorted(w["ticker"] for w in get("/api/watchlist")),
    "chat": [m["id"] for m in get("/api/chat/history")],
}, sort_keys=True))'
}

start
post /api/portfolio/trade '{"ticker":"AAPL","side":"buy","quantity":2}'
post /api/watchlist '{"ticker":"PYPL"}'
post /api/chat '{"message":"hello"}'
BEFORE=$(state)
echo "before: $BEFORE"
echo "$BEFORE" | grep -q '"AAPL"' && echo "$BEFORE" | grep -q '"PYPL"' \
  && echo "$BEFORE" | grep -q '"chat": \[".' && ! echo "$BEFORE" | grep -q '"cash": 10000.0' \
  || { echo "FAIL: mutations not visible before restart" >&2; exit 1; }

"$DOCKER" rm -f "$CONTAINER" >/dev/null
start
AFTER=$(state)
echo "after:  $AFTER"
[ "$BEFORE" = "$AFTER" ] || { echo "FAIL: state differs after restart" >&2; exit 1; }
echo "PERSISTENCE OK"
