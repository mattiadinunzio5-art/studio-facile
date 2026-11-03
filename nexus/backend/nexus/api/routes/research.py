from typing import Annotated, Literal

from fastapi import APIRouter, Query

from ...services import research as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas_research import AskIn, AskOut, RetrievalOut

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/search", response_model=RetrievalOut, summary="Ricerca testuale, semantica o ibrida nei documenti")
def search(
    db: DB, user: CurrentUser, settings: AppSettings,
    q: Annotated[str, Query(min_length=2, max_length=500)],
    mode: Literal["hybrid", "text", "semantic"] = "hybrid",
    limit: int = Query(10, ge=1, le=50),
):
    return svc.search(db, user, settings, q.strip(), mode, limit)


@router.post("/ask", response_model=AskOut, summary="Risposta basata sui documenti, con citazioni")
def ask(data: AskIn, db: DB, user: CurrentUser, settings: AppSettings):
    return svc.ask(db, user, settings, data.question, data.document_ids, data.limit)
