#!/usr/bin/env bash
# Build (if needed) and run the FinAlly container. Usage: start_mac.sh [--build]
set -euo pipefail

cd "$(dirname "$0")/.."
DOCKER="${DOCKER:-docker}"
IMAGE=finally
CONTAINER=finally
URL=http://localhost:8000

if [ ! -f .env ]; then
  echo "Warning: .env not found, creating it from .env.example. Add your OPENROUTER_API_KEY."
  cp .env.example .env
fi

if [ "${1:-}" = "--build" ] || ! "$DOCKER" image inspect "$IMAGE" >/dev/null 2>&1; then
  "$DOCKER" build -t "$IMAGE" .
fi

"$DOCKER" rm -f "$CONTAINER" >/dev/null 2>&1 || true
"$DOCKER" run -d --name "$CONTAINER" \
  -v finally-data:/app/db \
  -p 8000:8000 \
  --env-file .env \
  "$IMAGE" >/dev/null

echo "FinAlly is running at $URL"
if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi
