"""Accesso ai progetti condivisi e gestione dei membri.

Ruoli: owner (proprietario), editor (modifica i contenuti del progetto),
viewer (sola lettura). I documenti dell'archivio restano privati del
proprietario; si condividono progetti, rapporti e appunti del progetto.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..models import Project, ProjectMember, User
from . import activity, notifications

RANK = {"viewer": 1, "editor": 2, "owner": 3}


def role_in(db: Session, user: User, project_id: int | None) -> str | None:
    if project_id is None:
        return None
    p = db.get(Project, project_id)
    if p is None:
        return None
    if p.owner_id == user.id:
        return "owner"
    m = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id))
    return m.role if m else None


def require(db: Session, user: User, project_id: int, minimum: str = "viewer") -> tuple[Project, str]:
    role = role_in(db, user, project_id)
    if role is None:
        raise NotFoundError("Progetto non trovato.")
    if RANK[role] < RANK[minimum]:
        from .auth import ForbiddenError

        raise ForbiddenError("Permessi insufficienti su questo progetto.")
    return db.get(Project, project_id), role


def shared_project_ids(db: Session, user: User) -> list[int]:
    return list(db.scalars(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)))


def list_members(db: Session, user: User, project_id: int) -> list[dict]:
    p, _ = require(db, user, project_id, "viewer")
    owner = db.get(User, p.owner_id)
    rows = [{"user_id": owner.id, "email": owner.email, "display_name": owner.display_name, "role": "owner"}]
    for m, u in db.execute(select(ProjectMember, User).join(User, User.id == ProjectMember.user_id).where(ProjectMember.project_id == project_id)):
        rows.append({"user_id": u.id, "email": u.email, "display_name": u.display_name, "role": m.role})
    return rows


def add_member(db: Session, user: User, project_id: int, email: str, role: str, confirm: bool) -> list[dict]:
    p, _ = require(db, user, project_id, "owner")
    target = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower(), User.is_local.is_(False)))
    if target is None:
        raise ValidationFailedError("Nessun account con questa email.")
    if target.id == user.id:
        raise ValidationFailedError("Sei già il proprietario del progetto.")
    if not confirm:
        raise ConfirmationRequiredError(
            f"Condividere «{p.title}» con {target.email} come {role} richiede conferma (confirm=true).",
            details={"project": p.title, "email": target.email, "role": role},
        )
    m = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == target.id))
    if m:
        m.role = role
    else:
        db.add(ProjectMember(project_id=project_id, user_id=target.id, role=role))
    notifications.create(db, target, f"{user.display_name} ha condiviso con te il progetto «{p.title}»", f"Ruolo: {role}")
    activity.record(db, user=user, actor="user", action="project.share", entity_type="project", entity_id=p.id,
                    summary=f"Progetto «{p.title}» condiviso con {target.email} ({role})")
    db.commit()
    return list_members(db, user, project_id)


def remove_member(db: Session, user: User, project_id: int, member_user_id: int) -> list[dict]:
    p, role = require(db, user, project_id, "viewer")
    if role != "owner" and member_user_id != user.id:
        from .auth import ForbiddenError

        raise ForbiddenError("Solo il proprietario può rimuovere altri membri.")
    m = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == member_user_id))
    if m is None:
        raise NotFoundError("Membro non trovato.")
    db.delete(m)
    activity.record(db, user=user, actor="user", action="project.unshare", entity_type="project", entity_id=p.id, summary="Rimosso un membro dal progetto")
    db.commit()
    return list_members(db, user, project_id) if role == "owner" else []
