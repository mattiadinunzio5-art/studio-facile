from fastapi import APIRouter

from .routes import activity, connectors, dashboard, modules, notifications, projects, search, system

api_router = APIRouter(prefix="/api")
for r in (system, modules, dashboard, projects, activity, notifications, connectors, search):
    api_router.include_router(r.router)
