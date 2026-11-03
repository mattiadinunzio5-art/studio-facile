"""Punto d'ingresso dell'applicazione FastAPI.

Avvio locale::

    uvicorn nexus.main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.router import api_router
from .core.config import Settings, get_settings
from .core.errors import register_exception_handlers
from .core.logging import configure_logging, logger
from .database.migrate import upgrade_to_head
from .database.session import Database
from .services.bootstrap import bootstrap


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.auto_migrate:
            upgrade_to_head(settings.database_url)
        with app.state.database.session_factory() as db:
            bootstrap(db)
        logger.info("NEXUS %s avviato (%s, db=%s)", __version__, settings.env, settings.database_label)
        yield
        app.state.database.engine.dispose()

    app = FastAPI(
        title="NEXUS API",
        version=__version__,
        description="Historical & Financial Intelligence Platform — API REST.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = Database(settings.database_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
