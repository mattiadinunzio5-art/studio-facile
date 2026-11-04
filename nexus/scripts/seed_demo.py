"""Crea dati dimostrativi CHIARAMENTE ETICHETTATI (is_demo=True, badge DEMO).

Uso:  backend/.venv/bin/python scripts/seed_demo.py

Crea solo progetti vuoti di esempio: nessun dato storico o finanziario viene
inventato. Rieseguibile: non duplica i progetti già presenti.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from nexus.api.schemas import ProjectCreate  # noqa: E402
from nexus.core.config import get_settings  # noqa: E402
from nexus.database.migrate import upgrade_to_head  # noqa: E402
from nexus.database.session import Database  # noqa: E402
from nexus.models import Project  # noqa: E402
from nexus.services.bootstrap import bootstrap  # noqa: E402
from nexus.services.projects import create_project  # noqa: E402

DEMO_PROJECTS = [
    ProjectCreate(
        title="[DEMO] Progetto di esempio — crisi finanziarie",
        description="Progetto dimostrativo vuoto, creato da scripts/seed_demo.py. "
        "Non contiene dati: serve solo a provare l'interfaccia.",
    ),
    ProjectCreate(
        title="[DEMO] Progetto di esempio — storia monetaria",
        description="Progetto dimostrativo vuoto. Può essere eliminato in qualsiasi momento.",
    ),
]


def main() -> None:
    settings = get_settings()
    upgrade_to_head(settings.database_url)
    database = Database(settings.database_url)
    with database.session_factory() as db:
        user = bootstrap(db)
        existing = set(db.scalars(select(Project.title).where(Project.owner_id == user.id)))
        created = 0
        for p in DEMO_PROJECTS:
            if p.title not in existing:
                create_project(db, user, p, is_demo=True)
                created += 1
    print(f"Progetti DEMO creati: {created}")




# --- Eventi dimostrativi (Fase 3) ------------------------------------------------------------
# Fatti storici noti, ma inseriti SENZA fonti: restano «non verificati» e marcati DEMO finché
# l'utente non collega e verifica le fonti nella bibliografia.
DEMO_EVENTS = [
    dict(title="[DEMO] Crollo di Wall Street", start_year=1929, start_month=10, start_day=24, end_year=1929, end_month=10, end_day=29,
         countries=["Stati Uniti"], categories=["financial_crisis"], description="Crollo della borsa di New York nell'ottobre 1929."),
    dict(title="[DEMO] Conferenza di Bretton Woods", start_year=1944, start_month=7, start_day=1, end_year=1944, end_month=7, end_day=22,
         countries=["Stati Uniti"], categories=["monetary"], description="Conferenza monetaria e finanziaria delle Nazioni Unite."),
    dict(title="[DEMO] Sospensione della convertibilità del dollaro in oro", start_year=1971, start_month=8, start_day=15,
         countries=["Stati Uniti"], categories=["monetary"], description="Annuncio della sospensione della convertibilità del dollaro in oro."),
    dict(title="[DEMO] Introduzione dell'euro come moneta scritturale", start_year=1999, start_month=1, start_day=1,
         countries=["Unione europea"], categories=["monetary"], description="Avvio dell'euro per le transazioni non in contanti."),
    dict(title="[DEMO] Fallimento di Lehman Brothers", start_year=2008, start_month=9, start_day=15,
         countries=["Stati Uniti"], categories=["financial_crisis", "banking"], description="Istanza di fallimento della banca d'investimento."),
]


def seed_events() -> None:
    from nexus.api.schemas_history import EventIn
    from nexus.models import HistoricalEvent
    from nexus.services.history import create_event

    settings = get_settings()
    database = Database(settings.database_url)
    with database.session_factory() as db:
        user = bootstrap(db)
        existing = set(db.scalars(select(HistoricalEvent.title).where(HistoricalEvent.owner_id == user.id)))
        n = 0
        for e in DEMO_EVENTS:
            if e["title"] not in existing:
                create_event(db, user, EventIn(**e, reliability="unverified",
                                               reliability_note="Scheda dimostrativa senza fonti: verificare prima dell'uso."), is_demo=True)
                n += 1
    print(f"Eventi DEMO creati: {n}")


if __name__ == "__main__":
    main()
    seed_events()
