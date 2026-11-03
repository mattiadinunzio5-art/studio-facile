#!/usr/bin/env bash
# Avvia backend (127.0.0.1:8000) e frontend (127.0.0.1:5173) in sviluppo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/backend"
.venv/bin/uvicorn nexus.main:app --host 127.0.0.1 --port 8000 --reload &
BACK=$!
trap 'kill $BACK 2>/dev/null || true' EXIT INT TERM

cd "$ROOT/frontend"
npm run dev
