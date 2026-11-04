#!/usr/bin/env bash
# Avvia backend (127.0.0.1:8000) e frontend in sviluppo.
#
#   scripts/dev.sh          solo su questo computer: http://127.0.0.1:5173
#   scripts/dev.sh --lan    raggiungibile da telefono/tablet sulla stessa rete Wi-Fi
#
# Con --lan l'app è visibile da chiunque sia sulla tua rete, quindi viene avviata
# in modalità multi-utente con login obbligatorio (salvo NEXUS_AUTH_MODE già impostato).
# Il backend resta comunque su 127.0.0.1: il telefono passa dal frontend (proxy /api).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST=127.0.0.1

if [[ "${1:-}" == "--lan" ]]; then
  HOST=0.0.0.0
  export NEXUS_AUTH_MODE="${NEXUS_AUTH_MODE:-multi}"
  IP="$( (hostname -I 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || echo '') | awk '{print $1}')"
  echo "==> Modalità rete locale (login obbligatorio: NEXUS_AUTH_MODE=$NEXUS_AUTH_MODE)"
  echo "==> Dal telefono, sulla stessa rete Wi-Fi, apri: http://${IP:-<IP-del-computer>}:5173"
  echo "==> Al primo accesso registrati: il primo account diventa amministratore."
fi

cd "$ROOT/backend"
.venv/bin/uvicorn nexus.main:app --host 127.0.0.1 --port 8000 --reload &
BACK=$!
trap 'kill $BACK 2>/dev/null || true' EXIT INT TERM

cd "$ROOT/frontend"
npx vite --host "$HOST"
