"""Piani e limiti d'uso.

- ``local``: utente locale della modalità personale, nessun limite.
- ``free`` / ``premium``: piani per la modalità multi-utente (SaaS).

Nessun pagamento reale: il cambio di piano lo esegue un amministratore.
Un fornitore di pagamenti potrà essere collegato tramite ``billing.PaymentProvider``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .errors import NexusError


class QuotaExceededError(NexusError):
    status_code = 403
    code = "quota_exceeded"


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_note: str
    max_projects: int | None
    max_documents: int | None
    max_storage_mb: int | None
    max_series: int | None
    ai_runs_per_day: int | None


PLANS = {
    "local": Plan("local", "Locale (personale)", "Uso personale sul proprio computer", None, None, None, None, None),
    "free": Plan("free", "Gratuito", "Gratuito", 10, 100, 250, 50, 10),
    "premium": Plan("premium", "Premium", "Prezzo da definire: pagamenti non ancora attivi", 500, 10000, 20000, 2000, 200),
}


def plan_of(user) -> Plan:
    return PLANS.get(user.plan, PLANS["free"])


def usage(db: Session, user) -> dict:
    from ..models import Document, Project, ResearchRun, Series

    since = datetime.now(UTC) - timedelta(days=1)
    return {
        "projects": db.scalar(select(func.count()).select_from(Project).where(Project.owner_id == user.id)) or 0,
        "documents": db.scalar(select(func.count()).select_from(Document).where(Document.owner_id == user.id)) or 0,
        "storage_mb": round((db.scalar(select(func.coalesce(func.sum(Document.size_bytes), 0)).where(Document.owner_id == user.id)) or 0) / 1024 / 1024, 2),
        "series": db.scalar(select(func.count()).select_from(Series).where(Series.owner_id == user.id)) or 0,
        "ai_runs_today": db.scalar(select(func.count()).select_from(ResearchRun).where(
            ResearchRun.owner_id == user.id, ResearchRun.mode == "ai", ResearchRun.created_at >= since)) or 0,
    }


def enforce(db: Session, user, resource: str, extra_bytes: int = 0) -> None:
    plan = plan_of(user)
    if plan.id == "local":
        return
    u = usage(db, user)
    checks = {
        "projects": (u["projects"] + 1, plan.max_projects, "progetti"),
        "documents": (u["documents"] + 1, plan.max_documents, "documenti"),
        "series": (u["series"] + 1, plan.max_series, "serie"),
        "ai_runs": (u["ai_runs_today"] + 1, plan.ai_runs_per_day, "ricerche AI nelle ultime 24 ore"),
    }
    if resource in checks:
        value, limit, label = checks[resource]
        if limit is not None and value > limit:
            raise QuotaExceededError(f"Limite del piano {plan.name} raggiunto: massimo {limit} {label}.", details={"plan": plan.id, "limit": limit})
    if resource == "documents" and plan.max_storage_mb is not None and u["storage_mb"] + extra_bytes / 1024 / 1024 > plan.max_storage_mb:
        raise QuotaExceededError(f"Spazio del piano {plan.name} esaurito ({plan.max_storage_mb} MB).", details={"plan": plan.id})


def as_dict(plan: Plan) -> dict:
    return asdict(plan)
