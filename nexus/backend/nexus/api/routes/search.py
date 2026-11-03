from typing import Annotated

from fastapi import APIRouter, Query

from ...services import search as svc
from ..deps import DB, CurrentUser
from ..schemas import SearchQueryOut, SearchResultOut

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResultOut, summary="Ricerca globale")
def search(
    db: DB,
    user: CurrentUser,
    q: Annotated[str, Query(min_length=2, max_length=200)],
):
    return svc.search(db, user, q.strip())


@router.get("/recent", response_model=list[SearchQueryOut])
def recent(db: DB, user: CurrentUser):
    return svc.recent_queries(db, user)
