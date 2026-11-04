"""Gestione dei progetti di ricerca. Ogni operazione è limitata all'owner."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..api.schemas import ProjectCreate, ProjectUpdate
from ..core.errors import ConfirmationRequiredError, NotFoundError
from ..models import Project, User
from . import activity


def list_projects(db: Session, user: User, status: str | None = None, include_shared: bool = True) -> list[Project]:
    from . import sharing

    ids = sharing.shared_project_ids(db, user) if include_shared else []
    stmt = select(Project).where((Project.owner_id == user.id) | (Project.id.in_(ids)))
    if status:
        stmt = stmt.where(Project.status == status)
    return list(db.scalars(stmt.order_by(Project.updated_at.desc(), Project.id.desc())))


def count_by_status(db: Session, user: User) -> dict[str, int]:
    rows = db.execute(
        select(Project.status, func.count())
        .where(Project.owner_id == user.id)
        .group_by(Project.status)
    ).all()
    return {status: count for status, count in rows}


def get_project(db: Session, user: User, project_id: int, minimum: str = "viewer") -> Project:
    from . import sharing

    # Stessa risposta per "inesistente" e "di un altro utente": nessuna fuga di informazioni.
    project, _ = sharing.require(db, user, project_id, minimum)
    return project


def create_project(db: Session, user: User, data: ProjectCreate, is_demo: bool = False) -> Project:
    from ..core import plans

    plans.enforce(db, user, "projects")
    project = Project(
        owner_id=user.id, title=data.title, description=data.description, is_demo=is_demo
    )
    db.add(project)
    db.flush()
    activity.record(
        db,
        user=user,
        actor="user",
        action="project.create",
        entity_type="project",
        entity_id=project.id,
        summary=f"Creato il progetto «{project.title}»" + (" (DEMO)" if is_demo else ""),
    )
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, user: User, project_id: int, data: ProjectUpdate) -> Project:
    project = get_project(db, user, project_id, "editor")
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        return project
    for field, value in changes.items():
        setattr(project, field, value)
    action = "project.update"
    if changes.get("status") == "archived":
        action = "project.archive"
    elif changes.get("status") == "active":
        action = "project.restore" if len(changes) == 1 else action
    activity.record(
        db,
        user=user,
        actor="user",
        action=action,
        entity_type="project",
        entity_id=project.id,
        summary=f"Modificato il progetto «{project.title}» ({', '.join(sorted(changes))})",
    )
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, user: User, project_id: int, confirm: bool) -> None:
    project = get_project(db, user, project_id, "owner")
    if not confirm:
        raise ConfirmationRequiredError(
            "L'eliminazione è irreversibile e richiede conferma esplicita (confirm=true).",
            details={"project_id": project.id, "title": project.title},
        )
    title = project.title
    db.delete(project)
    activity.record(
        db,
        user=user,
        actor="user",
        action="project.delete",
        entity_type="project",
        entity_id=project_id,
        summary=f"Eliminato il progetto «{title}»",
    )
    db.commit()
