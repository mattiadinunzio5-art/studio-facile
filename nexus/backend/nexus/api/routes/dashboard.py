from fastapi import APIRouter

from ...services import dashboard, preferences
from ..deps import DB, AppSettings, CurrentUser
from ..schemas import DashboardLayout, DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut, summary="Dati aggregati della dashboard")
def get_dashboard(db: DB, user: CurrentUser, settings: AppSettings):
    return dashboard.build(db, user, settings)


@router.get("/layout", response_model=DashboardLayout)
def get_layout(db: DB, user: CurrentUser):
    return preferences.get_dashboard_layout(db, user)


@router.put("/layout", response_model=DashboardLayout, summary="Salva ordine e visibilità dei widget")
def put_layout(layout: DashboardLayout, db: DB, user: CurrentUser):
    return preferences.set_dashboard_layout(db, user, layout)
