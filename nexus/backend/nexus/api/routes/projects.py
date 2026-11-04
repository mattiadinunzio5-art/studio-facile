from typing import Literal

from fastapi import APIRouter, Query, status

from ...services import projects as svc
from ..deps import DB, CurrentUser
from pydantic import BaseModel

from ..schemas import ProjectCreate, ProjectOut, ProjectUpdate


class MemberIn(BaseModel):
    email: str
    role: Literal["viewer", "editor"] = "viewer"

router = APIRouter(prefix="/projects", tags=["projects"])


def _out(db, user, p) -> ProjectOut:
    from ...services import sharing

    out = ProjectOut.model_validate(p)
    out.my_role = sharing.role_in(db, user, p.id) or "viewer"
    return out


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: DB, user: CurrentUser, status_filter: Literal["active", "archived"] | None = Query(None, alias="status")
):
    return [_out(db, user, p) for p in svc.list_projects(db, user, status_filter)]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: DB, user: CurrentUser):
    return svc.create_project(db, user, data)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: DB, user: CurrentUser):
    return _out(db, user, svc.get_project(db, user, project_id))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, data: ProjectUpdate, db: DB, user: CurrentUser):
    return _out(db, user, svc.update_project(db, user, project_id, data))


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina un progetto (irreversibile: richiede confirm=true)",
)
def delete_project(project_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_project(db, user, project_id, confirm)


@router.get("/{project_id}/members", summary="Membri del progetto")
def list_members(project_id: int, db: DB, user: CurrentUser) -> list[dict]:
    from ...services import sharing

    return sharing.list_members(db, user, project_id)


@router.post("/{project_id}/members", summary="Condividi il progetto (richiede confirm=true)")
def add_member(project_id: int, data: MemberIn, db: DB, user: CurrentUser, confirm: bool = False) -> list[dict]:
    from ...services import sharing

    return sharing.add_member(db, user, project_id, data.email, data.role, confirm)


@router.delete("/{project_id}/members/{member_user_id}", summary="Rimuovi un membro (o abbandona il progetto)")
def remove_member(project_id: int, member_user_id: int, db: DB, user: CurrentUser) -> list[dict]:
    from ...services import sharing

    return sharing.remove_member(db, user, project_id, member_user_id)
