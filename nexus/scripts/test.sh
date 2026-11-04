#!/usr/bin/env bash
# Esegue tutti i test automatici (backend + frontend + typecheck).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "==> pytest";      (cd "$ROOT/backend" && .venv/bin/python -m pytest)
echo "==> typecheck";   (cd "$ROOT/frontend" && npx tsc -b)
echo "==> vitest";      (cd "$ROOT/frontend" && npx vitest run)
