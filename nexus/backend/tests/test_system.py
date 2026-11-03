def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_system_status_reports_local_ai_mode(client):
    body = client.get("/api/system/status").json()
    assert body["database_ok"] is True
    assert body["database"] == "SQLite"
    assert body["ai_mode"] == "local"
    assert body["ai_provider"]["id"] == "none"
    # I provider remoti esistono ma richiedono credenziali: senza, la modalità resta locale.
    assert all(p["requires_credentials"] for p in body["ai_providers"] if p["kind"] == "remote")


def test_unknown_ai_provider_falls_back_to_local(tmp_path):
    from fastapi.testclient import TestClient

    from nexus.core.config import Settings
    from nexus.main import create_app

    s = Settings(env="test", database_url=f"sqlite:///{tmp_path / 'x.db'}", ai_provider="anthropic")
    with TestClient(create_app(s)) as c:
        assert c.get("/api/system/status").json()["ai_provider"]["id"] == "none"


def test_me_is_local_user(client):
    body = client.get("/api/me").json()
    assert body["is_local"] is True


def test_unknown_route_returns_json_error(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_openapi_documents_all_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in [
        "/api/health",
        "/api/system/status",
        "/api/modules",
        "/api/dashboard",
        "/api/dashboard/layout",
        "/api/projects",
        "/api/projects/{project_id}",
        "/api/activity",
        "/api/notifications",
        "/api/connectors",
        "/api/connectors/{connector_id}/check",
        "/api/search",
    ]:
        assert p in paths, p


def test_unhandled_errors_return_generic_json_without_internals(settings):
    from fastapi.testclient import TestClient

    from nexus.main import create_app

    app = create_app(settings)

    @app.get("/api/_boom")
    def boom():
        raise RuntimeError("segreto interno")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/_boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "segreto" not in r.text
