def test_eight_modules_available_with_declared_features(client):
    mods = client.get("/api/modules").json()
    assert [m["code"] for m in mods] == list("ABCDEFGH")
    assert all(m["status"] == "available" for m in mods)
    # In Fase 1 nessun modulo analitico è dichiarato disponibile.
    assert {m["id"] for m in mods if m["status"] == "available"} >= {"historical", "time-machine", "knowledge-graph"}
    assert all(m["implemented_features"] for m in mods if m["status"] == "available")
    assert all(m["phase"] >= 2 for m in mods)
    assert all(m["planned_features"] for m in mods)


def test_get_single_module(client):
    assert client.get("/api/modules/financial").json()["phase"] == 4
    r = client.get("/api/modules/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
