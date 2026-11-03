def test_search_finds_projects_and_logs_query(client):
    client.post("/api/projects", json={"title": "Storia del gold standard", "description": "Dal 1870 al 1914"})
    body = client.get("/api/search?q=gold").json()
    assert [h["type"] for h in body["hits"]] == ["project"]
    # Dichiara gli ambiti non ancora ricercabili invece di simulare risultati.
    assert all("documenti" not in s for s in body["unavailable_scopes"])
    recent = client.get("/api/search/recent").json()
    assert recent[0]["query"] == "gold" and recent[0]["results_count"] == 1


def test_search_matches_modules(client):
    hits = client.get("/api/search?q=Knowledge").json()["hits"]
    assert any(h["type"] == "module" and h["id"] == "knowledge-graph" for h in hits)


def test_search_treats_wildcards_literally(client):
    client.post("/api/projects", json={"title": "Inflazione"})
    assert client.get("/api/search?q=%25%25").json()["hits"] == []
    assert client.get("/api/search?q=__").json()["hits"] == []


def test_search_validation(client):
    assert client.get("/api/search?q=a").status_code == 422
    assert client.get("/api/search").status_code == 422
    assert client.get("/api/search?q=" + "x" * 201).status_code == 422


def test_recent_searches_are_deduplicated(client):
    for q in ["oro", "argento", "ORO"]:
        client.get(f"/api/search?q={q}")
    assert [s["query"] for s in client.get("/api/search/recent").json()] == ["ORO", "argento"]


def test_global_search_includes_documents(client):
    from .factories import upload

    upload(client, "nota.txt", "Appunti sulla svalutazione della lira nel 1992.".encode())
    body = client.get("/api/search?q=svalutazione").json()
    assert any(h["type"] == "document" for h in body["hits"])
    assert "documenti" in body["searched_scopes"]
