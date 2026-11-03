from .factories import make_pdf, upload

DOCS = {
    "bw.txt": "La conferenza di Bretton Woods del 1944 creò il Fondo monetario internazionale e la Banca mondiale. "
    "Il sistema prevedeva cambi fissi con il dollaro convertibile in oro a 35 dollari l'oncia.",
    "crisi.txt": "Il crollo di Wall Street dell'ottobre 1929 aprì la Grande Depressione. "
    "La disoccupazione negli Stati Uniti salì drasticamente nei primi anni Trenta.",
    "euro.txt": "L'euro fu introdotto come moneta scritturale il 1 gennaio 1999 e in contanti nel 2002.",
}


def _load(client):
    for name, text in DOCS.items():
        assert upload(client, name, text.encode()).status_code == 201


def test_text_search_bm25(client):
    _load(client)
    hits = client.get("/api/research/search?q=Wall Street&mode=text").json()["hits"]
    assert hits[0]["document_title"] == "crisi"


def test_semantic_search_reports_engine(client):
    _load(client)
    body = client.get("/api/research/search?q=moneta unica europea contanti&mode=semantic").json()
    assert body["semantic_engine"].startswith("LSA")
    assert body["hits"][0]["document_title"] == "euro"


def test_hybrid_search_with_accents_and_inflection(client):
    _load(client)
    hits = client.get("/api/research/search?q=depressione disoccupazione").json()["hits"]
    assert hits and hits[0]["document_title"] == "crisi"
    assert hits[0]["support"] in ("strong", "partial")


def test_ask_returns_verbatim_claims_with_locators(client):
    upload(client, "bw.pdf", make_pdf(["Pagina introduttiva senza rilievo.", DOCS["bw.txt"]]), title="Storia BW")
    body = client.post("/api/research/ask", json={"question": "A quanto era convertibile il dollaro in oro?"}).json()
    assert body["mode"] == "local_extractive" and body["provider"] == "none"
    claim = body["claims"][0]
    assert claim["type"] == "documented_fact"
    passage = next(p for p in body["passages"] if p["chunk_id"] == claim["evidence"][0])
    assert claim["text"] in passage["text"]  # citazione letterale
    assert passage["page"] == 2 and passage["locator"] == "p. 2"
    assert "senza scheda bibliografica" in passage["source_label"]


def test_ask_without_evidence_reports_missing_data(client):
    _load(client)
    body = client.post("/api/research/ask", json={"question": "Produzione di grano in Mesopotamia"}).json()
    assert body["claims"][0]["type"] == "missing"
    assert body["claims"][0]["evidence"] == []


def test_ask_restricted_to_documents(client):
    _load(client)
    docs = {d["title"]: d["id"] for d in client.get("/api/documents").json()}
    body = client.post("/api/research/ask", json={"question": "euro introdotto", "document_ids": [docs["crisi"]]}).json()
    assert all(p["document_id"] == docs["crisi"] for p in body["passages"])


def test_search_is_isolated_per_user(client, db):
    from nexus.core.config import Settings
    from nexus.models import User
    from nexus.services import documents as docsvc

    other = User(email="o@x.org", display_name="Altro")
    db.add(other)
    db.commit()
    docsvc.import_bytes(db, other, client.app.state.settings, filename="s.txt", data=b"Segreto privato sul debito.")
    assert client.get("/api/research/search?q=segreto privato").json()["hits"] == []


def test_fts_query_syntax_is_neutralized(client):
    _load(client)
    for q in ['euro" OR "x', "NEAR(euro moneta)", "euro*", "-euro", "a:b"]:
        assert client.get("/api/research/search", params={"q": q}).status_code == 200
