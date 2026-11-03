from fastapi import APIRouter, Query

from ...services import activity as svc
from ..deps import DB, CurrentUser
from ..schemas import ActivityOut

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[ActivityOut], summary="Registro delle attività")
def list_activity(
    db: DB,
    user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return svc.list_for_user(db, user, limit=limit, offset=offset)
