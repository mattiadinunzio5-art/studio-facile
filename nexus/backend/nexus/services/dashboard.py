"""Aggregazione dei dati per la dashboard iniziale.

Ogni sezione contiene solo dati reali presenti nel database. Le sezioni che
dipendono da moduli non ancora sviluppati restituiscono ``UnavailableSection``
con il motivo e la fase prevista.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from ..agents.providers import AI_PROVIDERS
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
    from . import ai as ai_svc

    pid = ai_svc.effective_provider(db, user, settings)
    provider = next(p for p in AI_PROVIDERS if p.id == pid)

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
        indicators=_indicators(db, user),
        events=_events(db, user),
        reports=UnavailableSection(
            reason="La generazione e l'esportazione dei rapporti saranno disponibili con il Research Studio.",
            planned_phase=7,
        ),
        ai=_ai_activity(db, user, provider),
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


def _indicators(db: Session, user: User) -> DataSection | UnavailableSection:
    from ..models import Series
    from . import finance

    series = finance.list_series(db, user)
    if not series:
        return UnavailableSection(
            reason="Nessuna serie importata. Importa indicatori da World Bank, Eurostat, OWID o FRED (con chiave) nel modulo Financial Intelligence.",
            planned_phase=4,
        )
    items = []
    for s in series[:8]:
        out = finance.to_out(db, s)
        value = f"{out.last_value:,.4g} {s.unit}".strip() if out.last_value is not None else "nessun valore"
        items.append(DataItem(id=str(s.id), title=s.name, subtitle=value, date=f"ultimo dato {out.last_date or '—'}",
                              url=f"/financial/series/{s.id}", is_demo=s.is_demo))
    return DataSection(total=len(series), items=items,
                       note="Valori storici dell'ultima osservazione pubblicata dalla fonte, non quotazioni in tempo reale.")


def _ai_activity(db: Session, user: User, provider) -> AIActivity:
    from ..services import warroom

    runs = warroom.list_runs(db, user, limit=5)
    return AIActivity(
        mode="remote" if provider.kind == "remote" else "local",
        provider=provider.name,
        runs=[{"id": r.id, "question": r.question[:120], "status": r.status, "mode": r.mode, "provider": r.provider,
               "created_at": r.created_at.isoformat()} for r in runs],
        note="Nessun provider AI configurato: le ricerche usano il motore locale e gli agenti che richiedono un modello risultano non eseguiti."
        if provider.id == "none" else f"Provider selezionato: {provider.name}. Ogni run richiede approvazione finale.",
    )
