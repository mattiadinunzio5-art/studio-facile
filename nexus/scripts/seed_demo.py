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


if __name__ == "__main__":
    main()
