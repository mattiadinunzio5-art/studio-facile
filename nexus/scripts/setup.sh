#!/usr/bin/env bash
# Installa le dipendenze di backend e frontend (una tantum).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Backend (Python virtualenv)"
cd "$ROOT/backend"
if command -v uv >/dev/null 2>&1; then
  uv venv .venv -q
  uv pip install -q --python .venv/bin/python -r requirements-dev.txt
else
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements-dev.txt
fi

echo "==> Database (migrazioni)"
.venv/bin/alembic upgrade head

echo "==> Frontend (npm)"
cd "$ROOT/frontend"
npm install --no-fund --no-audit

echo "Pronto. Avvia con: scripts/dev.sh"
