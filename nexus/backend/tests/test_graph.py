def ent(client, name, t="person"):
    r = client.post("/api/graph/entities", json={"entity_type": t, "name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def rel(client, a, b, **kw):
    payload = {"source_entity_id": a, "target_entity_id": b, "relation_type": "influenced", "provenance": "user_hypothesis", **kw}
    return client.post("/api/graph/relations", json=payload)


def test_relation_requires_source_or_hypothesis_label(client):
    a, b = ent(client, "Keynes"), ent(client, "Bretton Woods", "institution")
    r = rel(client, a, b, provenance="sourced")
    assert r.status_code == 422 and "fonte" in str(r.json()["error"]["details"])
    s = client.post("/api/sources", json={"title": "Fonte"}).json()
    r = rel(client, a, b, provenance="sourced", source_id=s["id"])
    assert r.status_code == 201 and r.json()["evidence_label"].startswith("[Autore non indicato]")
    assert rel(client, a, b, relation_type="financed").json()["evidence_label"] == "Ipotesi dell'utente"


def test_ai_hypothesis_cannot_be_created_by_user(client):
    a, b = ent(client, "A"), ent(client, "B")
    assert rel(client, a, b, provenance="ai_hypothesis").status_code == 422


def test_relation_can_cite_document_passage(client):
    from .factories import upload

    d = upload(client, "t.txt", b"Keynes partecipo' alla conferenza.").json()
    chunk = client.get(f"/api/documents/{d['id']}/chunks").json()[0]
    a, b = ent(client, "Keynes"), ent(client, "Conferenza", "institution")
    r = rel(client, a, b, provenance="sourced", chunk_id=chunk["id"], relation_type="involved_in")
    assert r.status_code == 201 and r.json()["evidence_label"].startswith("t, ")


def test_self_loop_duplicate_and_foreign_entities(client, db):
    from nexus.models import Entity, User

    a, b = ent(client, "A"), ent(client, "B")
    assert rel(client, a, a).status_code == 422
    assert rel(client, a, b).status_code == 201
    assert rel(client, a, b).status_code == 422
    other = User(email="z@x.org", display_name="Z")
    db.add(other)
    db.flush()
    foreign = Entity(owner_id=other.id, entity_type="person", name="Estraneo")
    db.add(foreign)
    db.commit()
    assert rel(client, a, foreign.id).status_code == 404
    assert client.get(f"/api/graph/entities/{foreign.id}").status_code == 404


def test_explore_filters_and_layout(client):
    a, b, c, d = (ent(client, n) for n in "ABCD")
    rel(client, a, b), rel(client, b, c, relation_type="caused"), rel(client, c, d, relation_type="preceded")
    g = client.get(f"/api/graph?focus={a}&depth=1").json()
    assert {n["name"] for n in g["nodes"]} == {"A", "B"}
    assert all(isinstance(n["x"], float) for n in g["nodes"])
    g2 = client.get(f"/api/graph?focus={a}&depth=3&relation_types=influenced&relation_types=caused").json()
    assert {n["name"] for n in g2["nodes"]} == {"A", "B", "C"}
    full = client.get("/api/graph").json()
    assert full["stats"]["relations"] == 3 and full["stats"]["components"] == 1
    b_node = next(n for n in full["nodes"] if n["name"] == "B")
    assert b_node["betweenness"] > 0


def test_shortest_path(client):
    a, b, c, d = (ent(client, n) for n in "ABCD")
    rel(client, a, b), rel(client, c, b)
    p = client.get(f"/api/graph/path?source={a}&target={c}").json()
    assert p["found"] and p["entity_ids"] == [a, b, c] and len(p["relations"]) == 2
    assert client.get(f"/api/graph/path?source={a}&target={d}").json()["found"] is False


def test_event_entities_are_protected(client):
    e = client.post("/api/history/events", json={"title": "Evento", "start_year": 1900}).json()
    assert client.delete(f"/api/graph/entities/{e['entity_id']}?confirm=true").status_code == 422
    assert client.post("/api/graph/entities", json={"entity_type": "event", "name": "x"}).status_code == 422


def test_delete_entity_needs_confirm(client):
    a = ent(client, "A")
    assert client.delete(f"/api/graph/entities/{a}").status_code == 409
    assert client.delete(f"/api/graph/entities/{a}?confirm=true").status_code == 204
