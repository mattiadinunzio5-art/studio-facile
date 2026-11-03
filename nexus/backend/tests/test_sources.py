import httpx

from nexus.research import citations


def test_create_source_and_citation(client):
    r = client.post("/api/sources", json={
        "source_type": "book", "title": "Titolo di prova", "authors": ["Anna Bianchi"], "year": 2001,
        "publisher": "Editore", "isbn": "978-88-04-12345-7" if False else "",
    })
    assert r.status_code == 201
    s = r.json()
    assert s["verification_status"] == "unverified"
    assert s["citation"].startswith("Anna Bianchi. (2001). Titolo di prova")


def test_invalid_identifiers_rejected(client):
    for payload in ({"doi": "abc"}, {"isbn": "1234567890"}, {"url": "ftp://x"}, {"year": 3000}, {"accessed_at": "ieri"}):
        r = client.post("/api/sources", json={"title": "x", **payload})
        assert r.status_code == 422, payload


def test_isbn_and_doi_validation():
    assert citations.valid_isbn("0-306-40615-2") and citations.valid_isbn("978-0-306-40615-7")
    assert not citations.valid_isbn("978-0-306-40615-8")
    assert citations.valid_doi("https://doi.org/10.1000/xyz123")
    assert citations.normalize_doi("doi:10.1000/ABC") == "10.1000/ABC"


def test_user_verification_and_reset_on_edit(client):
    s = client.post("/api/sources", json={"title": "Fonte"}).json()
    v = client.post(f"/api/sources/{s['id']}/verify", json={"method": "user", "note": "Controllata in biblioteca"}).json()
    assert v["verification_status"] == "verified_user" and v["verified_at"]
    e = client.put(f"/api/sources/{s['id']}", json={"title": "Fonte modificata"}).json()
    assert e["verification_status"] == "unverified"


def test_registry_verification_requires_doi(client):
    s = client.post("/api/sources", json={"title": "Senza DOI"}).json()
    assert client.post(f"/api/sources/{s['id']}/verify", json={"method": "registry"}).status_code == 422


def test_crossref_lookup_parsing():
    payload = {"message": {"title": ["A Paper"], "author": [{"given": "Ada", "family": "Lovelace"}],
                           "issued": {"date-parts": [[1843]]}, "container-title": ["Journal"], "publisher": "P", "page": "1-10"}}
    ok = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))
    res = citations.crossref_lookup("10.1000/x", client=ok)
    assert res.status == "verified_registry" and res.metadata["authors"] == ["Ada Lovelace"] and res.metadata["year"] == 1843
    nf = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    assert citations.crossref_lookup("10.1000/x", client=nf).status == "not_found"


def test_registry_verification_flags_mismatch(client, monkeypatch):
    from nexus.services import sources as svc

    monkeypatch.setattr(svc, "crossref_lookup", lambda doi: citations.RegistryResult(
        "verified_registry", "Metadati confermati da Crossref.", {"title": "Titolo vero", "year": 2010}))
    s = client.post("/api/sources", json={"title": "Titolo sbagliato", "doi": "10.1000/abc", "year": 2011}).json()
    v = client.post(f"/api/sources/{s['id']}/verify", json={"method": "registry"}).json()
    assert v["verification_status"] == "verified_registry"
    assert "Discrepanze" in v["verification_note"] and "2010" in v["verification_note"]


def test_document_linked_to_source_cites_it(client):
    from .factories import upload

    s = client.post("/api/sources", json={"title": "Storia monetaria", "authors": ["Luca Verdi"], "year": 1990}).json()
    d = upload(client, "m.txt", b"La lira fu introdotta nel 1861 come moneta nazionale.").json()
    client.patch(f"/api/documents/{d['id']}", json={"source_id": s["id"]})
    hit = client.get("/api/research/search?q=lira moneta").json()["hits"][0]
    assert hit["source_label"].startswith("Luca Verdi. (1990)")


def test_delete_source_requires_confirmation(client):
    s = client.post("/api/sources", json={"title": "x"}).json()
    assert client.delete(f"/api/sources/{s['id']}").status_code == 409
    assert client.delete(f"/api/sources/{s['id']}?confirm=true").status_code == 204
