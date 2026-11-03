from fastapi import APIRouter

from .routes import (
    activity,
    connectors,
    dashboard,
    documents,
    modules,
    notifications,
    projects,
    research,
    search,
    sources,
    system,
)

api_router = APIRouter(prefix="/api")
for r in (system, modules, dashboard, projects, activity, notifications, connectors, search, documents, sources, research):
    api_router.include_router(r.router)
