from fastapi import APIRouter

from ...services import connectors as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas import ConnectorOut

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("", response_model=list[ConnectorOut], summary="Fonti esterne dichiarate e ultimo stato osservato")
def list_connectors(db: DB):
    return svc.list_connectors(db)


@router.post(
    "/{connector_id}/check",
    response_model=ConnectorOut,
    summary="Verifica la raggiungibilità della fonte (nessun dato scaricato)",
)
def check_connector(connector_id: str, db: DB, user: CurrentUser, settings: AppSettings):
    return svc.check_connector(db, user, connector_id, timeout=settings.connector_timeout)
