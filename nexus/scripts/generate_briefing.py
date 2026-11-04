"""Genera il Daily Briefing dalla riga di comando (programmabile con cron).

Uso:  backend/.venv/bin/python scripts/generate_briefing.py [--refresh] [--email utente@esempio]

Esempio di pianificazione (ogni giorno alle 7:10, crontab -e):
    10 7 * * * cd /percorso/nexus && backend/.venv/bin/python scripts/generate_briefing.py --refresh

Senza --email usa l'utente locale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from nexus.core.config import get_settings  # noqa: E402
from nexus.database.migrate import upgrade_to_head  # noqa: E402
from nexus.database.session import Database  # noqa: E402
from nexus.models import User  # noqa: E402
from nexus.services import briefing, notifications  # noqa: E402
from nexus.services.bootstrap import bootstrap  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera il NEXUS Daily Briefing")
    ap.add_argument("--refresh", action="store_true", help="Riscarica prima le serie dalle fonti")
    ap.add_argument("--email", help="Utente destinatario (predefinito: utente locale)")
    args = ap.parse_args()
    settings = get_settings()
    upgrade_to_head(settings.database_url)
    with Database(settings.database_url).session_factory() as db:
        user = db.scalar(select(User).where(User.email == args.email)) if args.email else bootstrap(db)
        if user is None:
            print(f"Utente non trovato: {args.email}", file=sys.stderr)
            return 1
        b = briefing.generate(db, user, settings, refresh_sources=args.refresh, trigger="scheduled")
        notifications.create(db, user, f"Daily Briefing del {b.content['date']} disponibile", "Generato automaticamente.")
        db.commit()
        print(f"Briefing #{b.id} generato ({len(b.content['sections'])} sezioni).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
