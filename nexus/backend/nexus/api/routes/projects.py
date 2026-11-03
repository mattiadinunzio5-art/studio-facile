from typing import Literal

from fastapi import APIRouter, Query, status

from ...services import projects as svc
from ..deps import DB, CurrentUser
from ..schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: DB, user: CurrentUser, status_filter: Literal["active", "archived"] | None = Query(None, alias="status")
):
    return svc.list_projects(db, user, status_filter)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: DB, user: CurrentUser):
    return svc.create_project(db, user, data)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: DB, user: CurrentUser):
    return svc.get_project(db, user, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, data: ProjectUpdate, db: DB, user: CurrentUser):
    return svc.update_project(db, user, project_id, data)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina un progetto (irreversibile: richiede confirm=true)",
)
def delete_project(project_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_project(db, user, project_id, confirm)
