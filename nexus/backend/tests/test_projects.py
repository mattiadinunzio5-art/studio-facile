import pytest

from nexus.models import Project, User


def _create(client, title="Crisi del 1929", description="Origini e propagazione"):
    r = client.post("/api/projects", json={"title": title, "description": description})
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_get_project(client):
    p = _create(client)
    assert p["status"] == "active"
    assert p["is_demo"] is False
    assert p["created_at"].endswith("Z") or "+00:00" in p["created_at"]
    assert client.get(f"/api/projects/{p['id']}").json()["title"] == "Crisi del 1929"


def test_title_is_trimmed(client):
    assert _create(client, title="   Bretton Woods  ")["title"] == "Bretton Woods"


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "   "}, {"title": "x" * 201}, {}, {"title": "ok", "description": "d" * 5001}],
)
def test_invalid_project_rejected(client, payload):
    r = client.post("/api/projects", json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_update_and_archive(client):
    p = _create(client)
    r = client.patch(f"/api/projects/{p['id']}", json={"title": "Grande Depressione"})
    assert r.json()["title"] == "Grande Depressione"
    r = client.patch(f"/api/projects/{p['id']}", json={"status": "archived"})
    assert r.json()["status"] == "archived"
    assert client.get("/api/projects?status=active").json() == []
    assert len(client.get("/api/projects?status=archived").json()) == 1


def test_invalid_status_rejected(client):
    p = _create(client)
    assert client.patch(f"/api/projects/{p['id']}", json={"status": "deleted"}).status_code == 422


def test_delete_requires_confirmation(client):
    p = _create(client)
    r = client.delete(f"/api/projects/{p['id']}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "confirmation_required"
    assert client.get(f"/api/projects/{p['id']}").status_code == 200
    assert client.delete(f"/api/projects/{p['id']}?confirm=true").status_code == 204
    assert client.get(f"/api/projects/{p['id']}").status_code == 404


def test_missing_project_404(client):
    assert client.get("/api/projects/9999").status_code == 404
    assert client.patch("/api/projects/9999", json={"title": "x"}).status_code == 404


def test_projects_are_isolated_per_owner(client, db):
    other = User(email="other@example.org", display_name="Altro")
    db.add(other)
    db.flush()
    db.add(Project(owner_id=other.id, title="Privato di un altro utente"))
    db.commit()
    foreign_id = db.query(Project).filter_by(owner_id=other.id).one().id

    assert client.get("/api/projects").json() == []
    assert client.get(f"/api/projects/{foreign_id}").status_code == 404
    assert client.delete(f"/api/projects/{foreign_id}?confirm=true").status_code == 404
    assert client.get("/api/search?q=Privato").json()["hits"] == []


def test_operations_are_logged(client):
    p = _create(client)
    client.patch(f"/api/projects/{p['id']}", json={"status": "archived"})
    client.delete(f"/api/projects/{p['id']}?confirm=true")
    actions = [a["action"] for a in client.get("/api/activity").json()]
    assert actions[:3] == ["project.delete", "project.archive", "project.create"]
    assert "system.init" in actions
