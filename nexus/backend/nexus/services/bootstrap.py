"""Inizializzazione al primo avvio: utente locale + notifica di benvenuto."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import ActivityLog, User
from ..security.identity import ensure_local_user
from . import activity, notifications


def bootstrap(db: Session) -> User:
    first_run = (db.scalar(select(func.count()).select_from(ActivityLog)) or 0) == 0
    user = ensure_local_user(db)
    if first_run:
        activity.record(
            db, user=None, actor="system", action="system.init", summary="Database NEXUS inizializzato"
        )
        notifications.create(
            db,
            user,
            title="Benvenuto in NEXUS — Fase 1",
            body="Fondamenta attive: dashboard, progetti, stato delle fonti, registro attività. "
            "I moduli analitici sono in preparazione e lo indicano esplicitamente.",
        )
        db.commit()
    return user
