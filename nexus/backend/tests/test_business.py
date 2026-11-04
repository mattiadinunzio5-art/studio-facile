"""Fase 8: account, sessioni, separazione dei dati, condivisione, piani, amministrazione."""

import pytest
from fastapi.testclient import TestClient

from nexus.core.config import Settings
from nexus.main import create_app
from nexus.services import auth as auth_svc

H = {"X-Nexus-Client": "web"}
PWD = "Archivio-Storico-2026"


@pytest.fixture
def app(tmp_path):
    s = Settings(env="test", database_url=f"sqlite:///{tmp_path / 'm.db'}", data_dir=tmp_path / "data", auth_mode="multi",
                 secret_key="test-key-multi")
    auth_svc.limiter._fails.clear()
    application = create_app(s)
    with TestClient(application):
        yield application


def browser(app):
    return TestClient(app)


def signup(app, email, name="U"):
    c = browser(app)
    r = c.post("/api/auth/register", json={"email": email, "password": PWD, "display_name": name})
    assert r.status_code == 201, r.text
    return c, r.json()


def test_auth_required_and_public_endpoints(app):
    c = browser(app)
    assert c.get("/api/auth/config").json() == {"mode": "multi", "allow_registration": True}
    assert c.get("/api/health").status_code == 200
    r = c.get("/api/projects")
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


def test_registration_rules_and_first_admin(app):
    a, ua = signup(app, "anna@example.org")
    b, ub = signup(app, "bruno@example.org")
    assert ua["role"] == "admin" and ub["role"] == "user" and ub["plan"] == "free"
    c = browser(app)
    assert c.post("/api/auth/register", json={"email": "x@example.org", "password": "corta1"}).status_code == 422
    assert c.post("/api/auth/register", json={"email": "ANNA@example.org", "password": PWD}).status_code == 422
    assert c.post("/api/auth/register", json={"email": "non-email", "password": PWD}).status_code == 422


def test_login_logout_and_rate_limit(app):
    signup(app, "carla@example.org")
    c = browser(app)
    for _ in range(5):
        assert c.post("/api/auth/login", json={"email": "carla@example.org", "password": "sbagliata-123"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "carla@example.org", "password": PWD}).status_code == 429
    auth_svc.limiter._fails.clear()
    assert c.post("/api/auth/login", json={"email": "Carla@Example.org", "password": PWD}).status_code == 200
    assert c.get("/api/me").json()["email"] == "carla@example.org"
    assert c.post("/api/auth/logout", headers=H).status_code == 204
    assert c.get("/api/me").status_code == 401


def test_cookie_is_httponly_and_csrf_header_required(app):
    c, _ = signup(app, "dario@example.org")
    cookie = c.cookies.jar
    assert any(ck.name == "nexus_session" and ck.has_nonstandard_attr("HttpOnly") for ck in cookie)
    r = c.post("/api/projects", json={"title": "Senza intestazione"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf"
    assert c.post("/api/projects", json={"title": "Con intestazione"}, headers=H).status_code == 201


def test_bearer_token_access(app):
    signup(app, "elsa@example.org")
    from nexus.services import auth

    with app.state.database.session_factory() as db:
        _, token = auth.login(db, app.state.settings, "elsa@example.org", PWD, "test", "1.2.3.4")
    c = browser(app)
    assert c.get("/api/me", headers={"Authorization": f"Bearer {token}"}).json()["email"] == "elsa@example.org"
    assert c.get("/api/me", headers={"Authorization": "Bearer falso"}).status_code == 401


def test_data_is_separated_between_users(app):
    a, _ = signup(app, "anna@example.org")
    b, _ = signup(app, "bruno@example.org")
    p = a.post("/api/projects", json={"title": "Progetto di Anna"}, headers=H).json()
    d = a.post("/api/documents", files={"file": ("n.txt", b"Appunti riservati sulla lira.")}, headers=H).json()
    s = a.post("/api/sources", json={"title": "Fonte di Anna"}, headers=H).json()
    a.post("/api/history/events", json={"title": "Evento di Anna", "start_year": 1900}, headers=H)
    assert b.get("/api/projects").json() == []
    assert b.get(f"/api/projects/{p['id']}").status_code == 404
    assert b.get(f"/api/documents/{d['id']}").status_code == 404
    assert b.get(f"/api/sources/{s['id']}").status_code == 404
    assert b.get("/api/history/events").json() == []
    assert b.get("/api/research/search?q=lira").json()["hits"] == []
    assert b.get("/api/search?q=Anna").json()["hits"] == []


def test_project_sharing_permissions(app):
    a, _ = signup(app, "anna@example.org")
    b, ub = signup(app, "bruno@example.org")
    p = a.post("/api/projects", json={"title": "Condiviso"}, headers=H).json()
    rep = a.post("/api/reports", json={"title": "Rapporto comune", "project_id": p["id"]}, headers=H).json()
    a.post("/api/notes", json={"title": "Nota", "project_id": p["id"]}, headers=H)
    r = a.post(f"/api/projects/{p['id']}/members", json={"email": "bruno@example.org", "role": "viewer"}, headers=H)
    assert r.status_code == 409 and r.json()["error"]["code"] == "confirmation_required"
    members = a.post(f"/api/projects/{p['id']}/members?confirm=true", json={"email": "bruno@example.org", "role": "viewer"}, headers=H).json()
    assert {m["role"] for m in members} == {"owner", "viewer"}
    assert b.get("/api/notifications").json()[0]["title"].endswith("«Condiviso»")
    shared = b.get("/api/projects").json()
    assert shared[0]["my_role"] == "viewer"
    assert b.patch(f"/api/projects/{p['id']}", json={"title": "x"}, headers=H).status_code == 403
    assert b.get(f"/api/reports/{rep['id']}").status_code == 200
    sec = rep["sections"][0]["id"]
    assert b.put(f"/api/reports/{rep['id']}/sections/{sec}", json={"body": "x"}, headers=H).status_code == 403
    assert len(b.get(f"/api/notes?project_id={p['id']}").json()) == 1
    a.post(f"/api/projects/{p['id']}/members?confirm=true", json={"email": "bruno@example.org", "role": "editor"}, headers=H)
    assert b.put(f"/api/reports/{rep['id']}/sections/{sec}", json={"body": "Scritto da Bruno"}, headers=H).status_code == 200
    assert b.delete(f"/api/reports/{rep['id']}?confirm=true", headers=H).status_code == 403
    assert b.delete(f"/api/projects/{p['id']}?confirm=true", headers=H).status_code == 403
    assert a.delete(f"/api/projects/{p['id']}/members/{ub['id']}", headers=H).status_code == 200
    assert b.get(f"/api/reports/{rep['id']}").status_code == 404


def test_plan_limits_and_admin_upgrade(app):
    a, _ = signup(app, "anna@example.org")
    b, ub = signup(app, "bruno@example.org")
    for i in range(10):
        assert b.post("/api/projects", json={"title": f"P{i}"}, headers=H).status_code == 201
    r = b.post("/api/projects", json={"title": "Undicesimo"}, headers=H)
    assert r.status_code == 403 and r.json()["error"]["code"] == "quota_exceeded"
    usage = b.get("/api/me/usage").json()
    assert usage["plan"]["id"] == "free" and usage["usage"]["projects"] == 10
    assert a.patch(f"/api/admin/users/{ub['id']}", json={"plan": "premium"}, headers=H).json()["plan"] == "premium"
    assert b.post("/api/projects", json={"title": "Undicesimo"}, headers=H).status_code == 201
    assert b.post("/api/billing/checkout/premium", headers=H).status_code == 501
    assert b.get("/api/billing/plans").json()["payments_enabled"] is False


def test_admin_area_protections(app):
    a, ua = signup(app, "anna@example.org")
    b, ub = signup(app, "bruno@example.org")
    assert b.get("/api/admin/users").status_code == 403
    users = a.get("/api/admin/users").json()
    assert {u["email"] for u in users} == {"anna@example.org", "bruno@example.org"}
    assert a.patch(f"/api/admin/users/{ua['id']}", json={"is_active": False}, headers=H).status_code == 422
    assert a.patch(f"/api/admin/users/{ua['id']}", json={"role": "user"}, headers=H).status_code == 422
    assert a.patch(f"/api/admin/users/{ub['id']}", json={"is_active": False}, headers=H).json()["is_active"] is False
    assert b.get("/api/me").status_code == 401  # sessioni chiuse alla disattivazione
    assert a.get("/api/admin/stats").json()["users"] == 2


def test_password_change_revokes_other_sessions(app):
    a, _ = signup(app, "anna@example.org")
    other = browser(app)
    other.post("/api/auth/login", json={"email": "anna@example.org", "password": PWD})
    assert other.get("/api/me").status_code == 200
    assert a.post("/api/auth/password", json={"current": "sbagliata", "new": "Nuova-Password-99"}, headers=H).status_code == 401
    assert a.post("/api/auth/password", json={"current": PWD, "new": "Nuova-Password-99"}, headers=H).status_code == 204
    assert a.get("/api/me").status_code == 200 and other.get("/api/me").status_code == 401
    assert len(a.get("/api/auth/sessions").json()) == 1


def test_expired_session(app):
    from datetime import timedelta

    from nexus.database.base import utcnow
    from nexus.models import AuthSession

    a, _ = signup(app, "anna@example.org")
    with app.state.database.session_factory() as db:
        for s in db.query(AuthSession).all():
            s.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    r = a.get("/api/me")
    assert r.status_code == 401 and "scaduta" in r.json()["error"]["message"]


def test_local_mode_unchanged(client):
    assert client.get("/api/auth/config").json()["mode"] == "local"
    assert client.post("/api/auth/register", json={"email": "a@b.org", "password": PWD}).status_code == 403
    u = client.get("/api/me/usage").json()
    assert u["plan"]["id"] == "local" and u["plan"]["max_projects"] is None
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
