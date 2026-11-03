from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nexus.core.config import Settings
from nexus.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(env="test", database_url=f"sqlite:///{tmp_path / 'test.db'}", auto_migrate=True)


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with TestClient(app) as c:  # esegue lifespan: migrazioni + bootstrap
        yield c


@pytest.fixture
def db(client):
    with client.app.state.database.session_factory() as session:
        yield session
