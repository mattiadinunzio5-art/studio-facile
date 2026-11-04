"""Ambiente Alembic. Usa i metadata dei modelli NEXUS."""

from __future__ import annotations

from alembic import context

from nexus.core.config import get_settings
from nexus.database.base import Base
from nexus.database.session import build_engine
import nexus.models  # noqa: F401  (registra le tabelle)

config = context.config
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # Le tabelle virtuali FTS5 (e le loro tabelle ombra) non sono gestite dall'ORM.
    if type_ == "table" and name and name.startswith("chunks_fts"):
        return False
    return True


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = build_engine(_url())
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # necessario per ALTER TABLE su SQLite
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
