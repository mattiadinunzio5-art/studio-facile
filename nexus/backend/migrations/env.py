"""Ambiente Alembic. Usa i metadata dei modelli NEXUS."""

from __future__ import annotations

from alembic import context

from nexus.core.config import get_settings
from nexus.database.base import Base
from nexus.database.session import build_engine
import nexus.models  # noqa: F401  (registra le tabelle)

config = context.config
target_metadata = Base.metadata


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
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
