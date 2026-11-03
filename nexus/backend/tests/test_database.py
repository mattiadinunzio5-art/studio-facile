from sqlalchemy import create_engine, inspect

from nexus.database.migrate import upgrade_to_head
from nexus.models import User

EXPECTED_TABLES = {
    "users",
    "projects",
    "activity_log",
    "notifications",
    "search_queries",
    "connector_states",
    "user_preferences",
    "alembic_version",
    "documents",
    "document_chunks",
    "sources",
    "chunks_fts",
}


def test_migrations_create_all_tables(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    upgrade_to_head(url)
    tables = set(inspect(create_engine(url)).get_table_names())
    assert EXPECTED_TABLES <= tables


def test_migrations_are_idempotent(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    upgrade_to_head(url)
    upgrade_to_head(url)  # nessun errore alla seconda esecuzione


def test_bootstrap_creates_single_local_user(client, db):
    users = db.query(User).all()
    assert len(users) == 1
    assert users[0].is_local is True


def test_bootstrap_is_idempotent(settings):
    from fastapi.testclient import TestClient

    from nexus.main import create_app

    for _ in range(2):
        with TestClient(create_app(settings)) as c:
            notes = c.get("/api/notifications").json()
    assert len(notes) == 1  # benvenuto creato una sola volta


def test_orm_matches_migrations(tmp_path):
    """Lo schema delle migrazioni deve coincidere con i modelli (nessuna migrazione mancante)."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from nexus.database.base import Base

    url = f"sqlite:///{tmp_path / 'm.db'}"
    upgrade_to_head(url)
    def include(obj, name, type_, *_):
        return not (type_ == "table" and name.startswith("chunks_fts"))

    with create_engine(url).connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"include_object": include})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == []
