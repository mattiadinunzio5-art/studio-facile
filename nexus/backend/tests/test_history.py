import pytest

CRASH = {
    "title": "Crollo di Wall Street", "start_year": 1929, "start_month": 10, "start_day": 24, "end_year": 1929, "end_month": 10,
    "end_day": 29, "countries": ["Stati Uniti"], "region": "Nord America", "categories": ["financial_crisis"],
    "description": "Crollo della borsa di New York.", "consequences": "Contribuì alla Grande Depressione.",
    "people": [], "institutions": ["NYSE"], "reliability": "established",
}
DEPRESSION = {"title": "Grande Depressione", "start_year": 1929, "end_year": 1939, "countries": ["Stati Uniti"],
              "categories": ["economic", "financial_crisis"], "consequences": "New Deal e riforme bancarie."}
BW = {"title": "Conferenza di Bretton Woods", "start_year": 1944, "start_month": 7, "countries": ["Stati Uniti"], "categories": ["monetary"]}


def ev(client, data):
    r = client.post("/api/history/events", json=data)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_event_with_all_fields(client):
    e = ev(client, CRASH)
    assert e["date_label"] == "24 ott 1929 – 29 ott 1929"
    assert e["entity_id"] is not None  # nodo nel Knowledge Graph
    assert "Nessuna fonte" in e["source_warning"]


@pytest.mark.parametrize("bad", [
    {"start_year": 0}, {"start_year": 1929, "start_month": 13}, {"start_year": 1929, "start_month": 2, "start_day": 30},
    {"start_year": 1930, "end_year": 1929}, {"start_year": 1929, "start_day": 3}, {"start_year": 1929, "categories": ["magia"]},
    {"start_year": 1929, "reliability": "certissimo"},
])
def test_invalid_dates_and_values(client, bad):
    assert client.post("/api/history/events", json={"title": "x", **bad}).status_code == 422


def test_bce_and_leap_dates(client):
    e = ev(client, {"title": "Idi di marzo", "start_year": -44, "start_month": 3, "start_day": 15})
    assert e["date_label"] == "15 mar 44 a.C."
    assert client.post("/api/history/events", json={"title": "x", "start_year": 2000, "start_month": 2, "start_day": 29}).status_code == 201
    assert client.post("/api/history/events", json={"title": "x", "start_year": 1900, "start_month": 2, "start_day": 29}).status_code == 422


def test_filters(client):
    ev(client, CRASH), ev(client, BW), ev(client, {"title": "Unificazione monetaria", "start_year": 1862, "countries": ["Italia"], "categories": ["monetary"]})
    assert [e["title"] for e in client.get("/api/history/events?category=monetary").json()] == ["Unificazione monetaria", "Conferenza di Bretton Woods"]
    assert [e["title"] for e in client.get("/api/history/events?country=italia").json()] == ["Unificazione monetaria"]
    assert len(client.get("/api/history/events?from_year=1930&to_year=1950").json()) == 1
    assert len(client.get("/api/history/events?q=wall").json()) == 1


def test_sources_and_verification_warning(client):
    e = ev(client, CRASH)
    s = client.post("/api/sources", json={"title": "Una storia della borsa"}).json()
    e2 = client.post(f"/api/history/events/{e['id']}/sources", json={"source_id": s["id"], "pages": "12-15"}).json()
    assert e2["sources"][0]["pages"] == "12-15" and "non sono ancora verificate" in e2["source_warning"]
    client.post(f"/api/sources/{s['id']}/verify", json={"method": "user"})
    assert client.get(f"/api/history/events/{e['id']}").json()["source_warning"] is None
    assert client.post(f"/api/history/events/{e['id']}/sources", json={"source_id": s["id"]}).status_code == 422
    assert client.post(f"/api/history/events/{e['id']}/sources", json={"source_id": 999}).status_code == 422


def test_delete_event_requires_confirmation_and_cascades_graph(client):
    a, b = ev(client, CRASH), ev(client, DEPRESSION)
    client.post(f"/api/history/events/{a['id']}/links", json={"target_event_id": b["id"], "relation_type": "caused", "provenance": "user_hypothesis"})
    assert client.delete(f"/api/history/events/{a['id']}").status_code == 409
    assert client.delete(f"/api/history/events/{a['id']}?confirm=true").status_code == 204
    assert client.get("/api/graph").json()["stats"]["relations"] == 0


def test_update_event_syncs_entity(client):
    e = ev(client, CRASH)
    client.put(f"/api/history/events/{e['id']}", json={**CRASH, "title": "Crash del 1929"})
    assert client.get(f"/api/graph/entities/{e['entity_id']}").json()["name"] == "Crash del 1929"


# --- Time Machine -----------------------------------------------------------------


def _knowledge(client, eid, content, year, kind):
    r = client.post(f"/api/history/events/{eid}/knowledge", json={"content": content, "known_since_year": year, "kind": kind})
    assert r.status_code == 200, r.text


def test_time_machine_hides_hindsight(client):
    crash, dep, bw = ev(client, CRASH), ev(client, DEPRESSION), ev(client, BW)
    _knowledge(client, crash["id"], "I giornali riportano vendite di panico.", 1929, "contemporary")
    _knowledge(client, crash["id"], "Studi successivi quantificano le perdite.", 1963, "historiography")

    t = client.get("/api/history/timeline?as_of_year=1931").json()
    titles = [e["title"] for e in t["events"]]
    assert "Conferenza di Bretton Woods" not in titles and t["hidden_future_events"] == 1
    c = next(e for e in t["events"] if e["title"] == "Crollo di Wall Street")
    assert c["consequences"] is None and c["consequences_hidden"] is True
    assert [k["content"] for k in c["known_then"]] == ["I giornali riportano vendite di panico."]
    assert c["known_later"] == [] and c["hidden_later_count"] == 1
    assert c["status_at_date"] == "concluded"
    d = next(e for e in t["events"] if e["title"] == "Grande Depressione")
    assert d["status_at_date"] == "ongoing"
    assert t["notes"] and "rigorosa" in t["notes"][0]


def test_time_machine_with_hindsight(client):
    crash = ev(client, CRASH)
    ev(client, BW)
    _knowledge(client, crash["id"], "Studi successivi.", 1963, "historiography")
    t = client.get("/api/history/timeline?as_of_year=1931&hindsight=true").json()
    assert len(t["events"]) == 2
    c = t["events"][0]
    assert c["consequences"] == CRASH["consequences"] and len(c["known_later"]) == 1


def test_contemporary_knowledge_cannot_predate_event(client):
    e = ev(client, BW)
    r = client.post(f"/api/history/events/{e['id']}/knowledge", json={"content": "x", "known_since_year": 1900, "kind": "contemporary"})
    assert r.status_code == 422


def test_timeline_without_date_shows_everything(client):
    ev(client, CRASH), ev(client, BW)
    t = client.get("/api/history/timeline").json()
    assert len(t["events"]) == 2 and all(e["status_at_date"] == "not_applicable" for e in t["events"])
