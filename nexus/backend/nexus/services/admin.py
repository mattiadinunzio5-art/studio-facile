"""Area amministratore: utenti, piani, stato degli account, statistiche."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core import plans
from ..core.errors import NotFoundError, ValidationFailedError
from ..models import AuthSession, Document, Project, ResearchRun, Series, User
from . import activity


def list_users(db: Session) -> list[dict]:
    out = []
    for u in db.scalars(select(User).order_by(User.id)):
        out.append({"id": u.id, "email": u.email, "display_name": u.display_name, "role": u.role, "plan": u.plan, "is_active": u.is_active,
                    "is_local": u.is_local, "created_at": u.created_at.isoformat(), "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                    "usage": plans.usage(db, u)})
    return out


def update_user(db: Session, admin: User, user_id: int, role: str | None, plan: str | None, is_active: bool | None) -> dict:
    u = db.get(User, user_id)
    if u is None:
        raise NotFoundError("Utente non trovato.")
    if u.is_local:
        raise ValidationFailedError("L'utente locale non è gestibile dall'area amministratore.")
    admins = db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))) or 0
    if u.id == admin.id and (is_active is False or (role and role != "admin")):
        raise ValidationFailedError("Non puoi disattivare o declassare il tuo stesso account.")
    if u.role == "admin" and admins <= 1 and (is_active is False or (role and role != "admin")):
        raise ValidationFailedError("Deve restare almeno un amministratore attivo.")
    if plan is not None:
        if plan not in ("free", "premium"):
            raise ValidationFailedError("Piano non valido.")
        u.plan = plan
    if role is not None:
        u.role = role
    if is_active is not None:
        u.is_active = is_active
        if not is_active:
            for s in db.scalars(select(AuthSession).where(AuthSession.user_id == u.id)):
                db.delete(s)
    activity.record(db, user=admin, actor="user", action="admin.user_update", entity_type="user", entity_id=u.id,
                    summary=f"Aggiornato l'account {u.email}: ruolo {u.role}, piano {u.plan}, {'attivo' if u.is_active else 'disattivato'}")
    db.commit()
    return next(x for x in list_users(db) if x["id"] == u.id)


def stats(db: Session) -> dict:
    def count(model):
        return db.scalar(select(func.count()).select_from(model)) or 0

    return {"users": count(User), "active_users": db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0,
            "projects": count(Project), "documents": count(Document), "series": count(Series), "research_runs": count(ResearchRun),
            "plans": {p: db.scalar(select(func.count()).select_from(User).where(User.plan == p)) or 0 for p in plans.PLANS}}
