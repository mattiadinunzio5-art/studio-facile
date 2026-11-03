from fastapi import APIRouter

from .routes import (
    activity,
    connectors,
    credentials,
    finance,
    dashboard,
    documents,
    graph,
    history,
    modules,
    notifications,
    projects,
    research,
    search,
    sources,
    system,
)

api_router = APIRouter(prefix="/api")
for r in (system, modules, dashboard, projects, activity, notifications, connectors, search, documents, sources, research, history, graph, finance, credentials):
    api_router.include_router(r.router)
