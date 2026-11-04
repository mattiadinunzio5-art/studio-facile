from fastapi import APIRouter, status

from ...services import sources as svc
from ..deps import DB, CurrentUser
from ..schemas_research import SourceIn, SourceOut, SourceVerifyIn

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: DB, user: CurrentUser, q: str | None = None):
    return [svc.to_out(s) for s in svc.list_sources(db, user, q)]


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_source(data: SourceIn, db: DB, user: CurrentUser):
    return svc.to_out(svc.create_source(db, user, data))


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: DB, user: CurrentUser):
    return svc.to_out(svc.get_source(db, user, source_id))


@router.put("/{source_id}", response_model=SourceOut)
def update_source(source_id: int, data: SourceIn, db: DB, user: CurrentUser):
    return svc.to_out(svc.update_source(db, user, source_id, data))


@router.post("/{source_id}/verify", response_model=SourceOut,
             summary="Verifica: dichiarazione dell'utente o controllo DOI su Crossref")
def verify_source(source_id: int, data: SourceVerifyIn, db: DB, user: CurrentUser):
    return svc.to_out(svc.verify_source(db, user, source_id, data.method, data.note))


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_source(db, user, source_id, confirm)
