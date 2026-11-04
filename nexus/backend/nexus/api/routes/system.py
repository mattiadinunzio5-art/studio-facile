from fastapi import APIRouter

from ... import __version__
from ...services import system
from ..deps import DB, AppSettings, CurrentUser
from ..schemas import HealthOut, SystemStatusOut, UserOut

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut, summary="Verifica che il backend risponda")
def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__)


@router.get("/system/status", response_model=SystemStatusOut, summary="Stato di database e modalità AI")
def system_status(db: DB, settings: AppSettings, user: CurrentUser) -> SystemStatusOut:
    return system.status(db, settings, user)


@router.get("/me", response_model=UserOut, summary="Utente corrente (Fase 1: utente locale)")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
