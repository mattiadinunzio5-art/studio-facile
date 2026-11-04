import io

import pytest

from nexus.studio import citations


def _report(client, **kw):
    r = client.post("/api/reports", json={"title": "Il debito pubblico italiano", "author": "Autore", **kw})
    assert r.status_code == 201, r.text
    return r.json()


def _fill(client, rep, body_by_key):
    for s in rep["sections"]:
        if s["key"] in body_by_key:
            r = client.put(f"/api/reports/{rep['id']}/sections/{s['id']}", json={"body": body_by_key[s["key"]]})
            assert r.status_code == 200, r.text
            rep = r.json()
    return rep


ALL = {k: f"Testo della sezione {k}." for k in ("abstract", "introduction", "methodology", "analysis", "evidence", "counterarguments", "conclusions", "limitations")}


def test_report_has_ten_part_structure(client):
    rep = _report(client)
    assert [s["key"] for s in rep["sections"]] == ["abstract", "introduction", "methodology", "analysis", "evidence", "counterarguments", "conclusions", "limitations"]
    # Titolo e bibliografia completano le 10 parti richieste.
    assert rep["title"] and rep["status"] == "draft"


def test_citation_parsing_and_rendering():
    text = "Come mostrato [@3, p. 12] e ancora [@7] e [@3]."
    assert citations.cited_ids([text]) == [3, 7]
    assert citations.render(text, {3: 1, 7: 2}) == "Come mostrato [1, p. 12] e ancora [2] e [1]."
    assert citations.render("[@99]", {}) == "[citazione non valida]"


def test_check_flags_invalid_and_unverified_citations(client):
    s = client.post("/api/sources", json={"title": "Storia del debito", "authors": ["A. Rossi"], "year": 2010}).json()
    rep = _report(client)
    rep = _fill(client, rep, {**ALL, "analysis": f"Secondo la fonte [@{s['id']}, p. 4] il debito crebbe. Vedi anche [@9999]."})
    c = client.get(f"/api/reports/{rep['id']}/check").json()
    assert c["invalid_citations"] == [9999] and c["ready"] is False
    assert c["unverified_sources"][0]["id"] == s["id"]
    r = client.post(f"/api/reports/{rep['id']}/status?value=approved")
    assert r.status_code == 422 and r.json()["error"]["details"]["invalid_citations"] == [9999]


def test_approval_and_edit_returns_to_draft(client):
    s = client.post("/api/sources", json={"title": "Fonte"}).json()
    rep = _fill(client, _report(client), {**ALL, "analysis": f"Testo [@{s['id']}]."})
    assert client.post(f"/api/reports/{rep['id']}/status?value=approved").json()["status"] == "approved"
    sec = rep["sections"][0]
    r = client.put(f"/api/reports/{rep['id']}/sections/{sec['id']}", json={"body": "Modificato"}).json()
    assert r["status"] == "draft"


def test_empty_sections_block_approval(client):
    rep = _report(client)
    c = client.get(f"/api/reports/{rep['id']}/check").json()
    assert len(c["empty_sections"]) == 8 and not c["ready"]


def test_chapters_add_move_delete_and_protect_standard_sections(client):
    rep = _report(client)
    rep = client.post(f"/api/reports/{rep['id']}/chapters", json={"title": "Il caso italiano", "after_key": "analysis"}).json()
    keys = [s["key"] for s in sorted(rep["sections"], key=lambda x: x["ordinal"])]
    assert keys.index("chapter") == keys.index("analysis") + 1
    ch = next(s for s in rep["sections"] if s["key"] == "chapter")
    rep = client.post(f"/api/reports/{rep['id']}/chapters/{ch['id']}/move?direction=1", json={}).json()
    keys = [s["key"] for s in sorted(rep["sections"], key=lambda x: x["ordinal"])]
    assert keys.index("chapter") == keys.index("evidence") + 1
    std = next(s for s in rep["sections"] if s["key"] == "abstract")
    assert client.delete(f"/api/reports/{rep['id']}/chapters/{std['id']}").status_code == 422
    assert client.put(f"/api/reports/{rep['id']}/sections/{std['id']}", json={"title": "Altro"}).status_code == 422
    rep = client.delete(f"/api/reports/{rep['id']}/chapters/{ch['id']}").json()
    assert all(s["key"] != "chapter" for s in rep["sections"])


def test_embeds_validation(client):
    rep = _report(client)
    sid = rep["sections"][3]["id"]
    bad = client.put(f"/api/reports/{rep['id']}/sections/{sid}", json={"embeds": [{"type": "table", "columns": ["a", "b"], "rows": [["1"]]}]})
    assert bad.status_code == 422
    ok = client.put(f"/api/reports/{rep['id']}/sections/{sid}", json={"embeds": [{"type": "table", "caption": "T", "columns": ["a", "b"], "rows": [["1", "2"]]},
                                                                              {"type": "series", "series_id": 999}]})
    assert ok.status_code == 200
    assert any("inesistente" in p for p in client.get(f"/api/reports/{rep['id']}/check").json()["embed_problems"])


def _series(client):
    csv = "anno,valore\n2015,132\n2016,134\n2017,134\n2018,134\n2019,134\n2020,155\n"
    return client.post("/api/finance/series/upload", files={"file": ("d.csv", csv.encode())}, data={"name": "Debito/PIL", "source_label": "Dati di prova", "unit": "% PIL", "category": "public_debt"}).json()["id"]


def test_pdf_and_docx_export_contain_content_citations_and_marks(client):
    import docx
    import pymupdf

    src = client.post("/api/sources", json={"title": "Storia del debito", "authors": ["A. Rossi"], "year": 2010}).json()
    sim = client.post("/api/lab/simulations/debt", json={"d0": 135, "r_eff0": 0.03, "r_market": 0.04, "g": 0.03, "years": 5, "rate_shock": 0.01}).json()
    rep = _fill(client, _report(client), {**ALL, "analysis": f"Il debito è cresciuto nel 2020 [@{src['id']}, p. 4].\n\nSecondo paragrafo con è, à, €.",
                                          "evidence": "- primo punto\n- secondo punto"})
    sec = next(s for s in rep["sections"] if s["key"] == "evidence")
    client.put(f"/api/reports/{rep['id']}/sections/{sec['id']}", json={"embeds": [
        {"type": "series", "series_id": _series(client), "caption": "Debito/PIL"},
        {"type": "simulation", "simulation_id": sim["id"]},
        {"type": "table", "caption": "Tabella 1", "columns": ["Anno", "Valore"], "rows": [["2020", "155"]]},
    ]})
    pdf = client.get(f"/api/reports/{rep['id']}/export/pdf")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    doc = pymupdf.open(stream=pdf.content, filetype="pdf")
    text = "".join(p.get_text() for p in doc)
    assert "Il debito pubblico italiano" in text and "[1, p. 4]" in text and "Bibliografia" in text
    assert "A. Rossi. (2010). Storia del debito" in text and "Fonte non verificata" in text
    assert "BOZZA" in text and "è, à, €" in text and "Tabella 1" in text
    assert sum(len(p.get_images()) for p in doc) >= 2
    d = client.get(f"/api/reports/{rep['id']}/export/docx")
    assert d.status_code == 200
    w = docx.Document(io.BytesIO(d.content))
    body = "\n".join(p.text for p in w.paragraphs)
    assert "[1, p. 4]" in body and "Bibliografia" in body and len(w.inline_shapes) >= 2 and len(w.tables) == 1
    assert client.get(f"/api/reports/{rep['id']}/export/txt").status_code == 422


def test_report_from_approved_research_run(client):
    from .factories import upload

    s = client.post("/api/sources", json={"title": "Bretton Woods, una storia", "year": 1990}).json()
    d = upload(client, "bw.txt", "La conferenza di Bretton Woods del 1944 stabilì cambi fissi con il dollaro convertibile in oro.".encode()).json()
    client.patch(f"/api/documents/{d['id']}", json={"source_id": s["id"]})
    run = client.post("/api/research/runs", json={"question": "Cosa stabilì la conferenza di Bretton Woods?"}).json()
    assert client.post(f"/api/reports/from-run/{run['id']}").status_code == 422  # non ancora approvata
    client.post(f"/api/research/runs/{run['id']}/decision", json={"decision": "approve"})
    rep = client.post(f"/api/reports/from-run/{run['id']}").json()
    body = {x["key"]: x["body"] for x in rep["sections"]}
    assert rep["origin"] == f"research_run:{run['id']}" and rep["contains_ai_text"] is False
    assert f"[@{s['id']}]" in body["analysis"] and "[Fatto documentato]" in body["analysis"]
    assert "motore locale" in body["methodology"]
    assert client.get(f"/api/reports/{rep['id']}/check").json()["invalid_citations"] == []


def test_notes_crud_and_validation(client):
    p = client.post("/api/projects", json={"title": "P"}).json()
    n = client.post("/api/notes", json={"title": "Appunto", "body": "Testo", "project_id": p["id"]})
    assert n.status_code == 201
    assert client.post("/api/notes", json={"title": "x", "source_id": 999}).status_code == 422
    assert len(client.get(f"/api/notes?project_id={p['id']}").json()) == 1
    nid = n.json()["id"]
    assert client.put(f"/api/notes/{nid}", json={"title": "Nuovo"}).json()["title"] == "Nuovo"
    assert client.delete(f"/api/notes/{nid}").status_code == 409
    assert client.delete(f"/api/notes/{nid}?confirm=true").status_code == 204


def test_daily_briefing_declares_missing_data_and_sources(client):
    b = client.post("/api/briefings", json={}).json()
    secs = {s["key"]: s for s in b["content"]["sections"]}
    assert len(secs) == 8
    assert secs["global_economy"]["empty_reason"] and secs["geopolitics"]["empty_reason"].startswith("NEXUS non dispone")
    _series(client)
    client.post("/api/history/events", json={"title": "Evento monetario", "start_year": 1971, "categories": ["monetary"]})
    b2 = client.post("/api/briefings", json={"refresh_sources": True}).json()
    secs = {s["key"]: s for s in b2["content"]["sections"]}
    item = secs["macro"]["items"][0]
    assert item["source"] == "Dati di prova" and item["date"] == "2020-01-01" and any("non essere aggiornata" in f for f in item["flags"])
    assert secs["historical_links"]["items"][0]["source"] == "Archivio storico NEXUS"
    assert all(i.get("date") for s in secs.values() for i in s["items"])
    assert len(client.get("/api/briefings").json()) == 2


def test_dashboard_and_search_include_reports(client):
    _report(client)
    d = client.get("/api/dashboard").json()["reports"]
    assert d["available"] and d["items"][0]["subtitle"] == "bozza"
    assert any(h["type"] == "report" for h in client.get("/api/search?q=debito").json()["hits"])
