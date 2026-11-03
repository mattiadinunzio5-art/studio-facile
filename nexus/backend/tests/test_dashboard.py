from nexus.api.schemas import ALL_WIDGETS


def test_dashboard_contains_only_real_or_declared_unavailable_data(client):
    client.post("/api/projects", json={"title": "Debito pubblico italiano"})
    d = client.get("/api/dashboard").json()
    assert len(d["modules"]) == 8
    assert d["projects"]["active_count"] == 1
    assert d["projects"]["items"][0]["title"] == "Debito pubblico italiano"
    for key, phase in (("indicators", 4), ("reports", 7), ("events", 3)):
        assert d[key]["available"] is False
        assert d[key]["planned_phase"] == phase
        assert d[key]["reason"]
    assert d["ai"]["mode"] == "local" and d["ai"]["runs"] == []
    assert d["sources"]["total"] == 8 and d["sources"]["implemented"] == 5
    assert d["notifications"]["unread_count"] == 1
    assert d["layout"]["order"] == ALL_WIDGETS


def test_layout_roundtrip_and_normalization(client):
    r = client.put("/api/dashboard/layout", json={"order": ["projects", "modules"], "hidden": ["events"]})
    assert r.status_code == 200
    body = r.json()
    assert body["order"][:2] == ["projects", "modules"]
    assert set(body["order"]) == set(ALL_WIDGETS)  # widget mancanti aggiunti in coda
    assert client.get("/api/dashboard").json()["layout"]["hidden"] == ["events"]


def test_layout_rejects_unknown_or_duplicate_widgets(client):
    assert client.put("/api/dashboard/layout", json={"order": ["hack"]}).status_code == 422
    assert client.put("/api/dashboard/layout", json={"order": ["projects", "projects"]}).status_code == 422


def test_dashboard_events_section_real_data(client):
    assert client.get("/api/dashboard").json()["events"]["available"] is False
    client.post("/api/history/events", json={"title": "Fondazione della Banca d'Inghilterra", "start_year": 1694})
    ev = client.get("/api/dashboard").json()["events"]
    assert ev["available"] is True and ev["total"] == 1 and ev["items"][0]["date"] == "1694"
