"""Aggregazione dei dati per la dashboard iniziale.

Ogni sezione contiene solo dati reali presenti nel database. Le sezioni che
dipendono da moduli non ancora sviluppati restituiscono ``UnavailableSection``
con il motivo e la fase prevista.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from ..agents.providers import active_provider
from ..api.schemas import (
    ActivityOut,
    AIActivity,
    DataItem,
    DataSection,
    DashboardOut,
    ModuleOut,
    NotificationOut,
    NotificationsSummary,
    ProjectOut,
    ProjectsSummary,
    SearchQueryOut,
    SourcesSummary,
    UnavailableSection,
)
from ..core.config import Settings
from ..core.modules import MODULES
from ..database.base import utcnow
from ..models import User
from . import activity, connectors, notifications, preferences, projects, search


def build(db: Session, user: User, settings: Settings) -> DashboardOut:
    conns = connectors.list_connectors(db)
    proj_counts = projects.count_by_status(db, user)
    active = projects.list_projects(db, user, status="active")[:6]
    provider = active_provider(settings.ai_provider)

    return DashboardOut(
        generated_at=utcnow(),
        layout=preferences.get_dashboard_layout(db, user),
        modules=[ModuleOut(**m.__dict__) for m in MODULES],
        sources=SourcesSummary(
            total=len(conns),
            implemented=sum(1 for c in conns if c.implemented),
            by_status=dict(Counter(c.last_status for c in conns)),
            items=conns,
        ),
        recent_searches=[SearchQueryOut.model_validate(q) for q in search.recent_queries(db, user)],
        projects=ProjectsSummary(
            active_count=proj_counts.get("active", 0),
            archived_count=proj_counts.get("archived", 0),
            items=[ProjectOut.model_validate(p) for p in active],
        ),
        indicators=UnavailableSection(
            reason="Nessuna serie economica importata. I connettori a fonti aperte saranno attivi con il modulo Financial Intelligence.",
            planned_phase=4,
        ),
        events=_events(db, user),
        reports=UnavailableSection(
            reason="La generazione e l'esportazione dei rapporti saranno disponibili con il Research Studio.",
            planned_phase=7,
        ),
        ai=AIActivity(
            mode="local" if provider.kind == "local" else "remote",
            provider=provider.name,
            runs=[],
            note="Nessun modello AI è stato eseguito. Gli agenti di ricerca arriveranno in Fase 5 e "
            "useranno un provider esterno solo se configurato dall'utente.",
        ),
        notifications=NotificationsSummary(
            unread_count=notifications.unread_count(db, user),
            items=[NotificationOut.model_validate(n) for n in notifications.list_for_user(db, user, limit=5)],
        ),
        recent_activity=[ActivityOut.model_validate(a) for a in activity.list_for_user(db, user, limit=8)],
    )


def _events(db: Session, user: User) -> DataSection | UnavailableSection:
    from sqlalchemy import func, select

    from ..history import dates
    from ..models import HistoricalEvent

    total = db.scalar(select(func.count()).select_from(HistoricalEvent).where(HistoricalEvent.owner_id == user.id)) or 0
    if total == 0:
        return UnavailableSection(reason="L'archivio storico è vuoto: crea o importa il primo evento.", planned_phase=3)
    recent = db.scalars(
        select(HistoricalEvent).where(HistoricalEvent.owner_id == user.id).order_by(HistoricalEvent.updated_at.desc()).limit(6)
    )
    return DataSection(
        total=total,
        items=[
            DataItem(id=str(e.id), title=e.title, subtitle=e.reliability,
                     date=dates.fmt_range(e.start_year, e.start_month, e.start_day, e.end_year, e.end_month, e.end_day),
                     url=f"/history/events/{e.id}", is_demo=e.is_demo)
            for e in recent
        ],
    )
