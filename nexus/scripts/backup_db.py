"""Backup consistente del database SQLite (API di backup di SQLite).

Uso:  backend/.venv/bin/python scripts/backup_db.py [cartella_destinazione]

Il backup è sicuro anche con l'applicazione in esecuzione. Per PostgreSQL
usare pg_dump (non gestito da questo script).
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from nexus.core.config import PROJECT_ROOT, get_settings  # noqa: E402


def main() -> int:
    settings = get_settings()
    if not settings.is_sqlite:
        print("Backup supportato solo per SQLite. Per PostgreSQL usa pg_dump.", file=sys.stderr)
        return 2
    src = Path(settings.database_url.split("///", 1)[1])
    if not src.exists():
        print(f"Database non trovato: {src}", file=sys.stderr)
        return 1
    dest_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "backups"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"nexus-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.db"
    with sqlite3.connect(src) as s, sqlite3.connect(dest) as d:
        s.backup(d)
    print(f"Backup creato: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
