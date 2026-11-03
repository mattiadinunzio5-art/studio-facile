"""Research Studio: rapporti, capitoli, appunti, citazioni verificabili, esportazione."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_studio import ChapterIn, NoteIn, ReportCheck, ReportCreate, ReportUpdate, SectionIn
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..models import Document, Note, Project, Report, ReportSection, ResearchRun, Series, SimulationRun, Source, User
from ..models.studio import STANDARD_SECTIONS
from ..research.citations import VERIFICATION_LABEL, format_citation
from ..studio import charts, citations, export
from . import activity

VERIFIED = ("verified_user", "verified_registry")


def _project(db: Session, user: User, project_id: int | None) -> None:
    if project_id is not None:
        p = db.get(Project, project_id)
        if p is None or p.owner_id != user.id:
            raise ValidationFailedError("Progetto inesistente.")


def create_report(db: Session, user: User, data: ReportCreate, origin: str = "manual") -> Report:
    _project(db, user, data.project_id)
    r = Report(owner_id=user.id, origin=origin, **data.model_dump())
    r.sections = [ReportSection(ordinal=i, key=k, title=t, body="", embeds=[]) for i, (k, t) in enumerate(STANDARD_SECTIONS)]
    db.add(r)
    db.flush()
    activity.record(db, user=user, actor="user", action="report.create", entity_type="report", entity_id=r.id, summary=f"Creato il rapporto «{r.title}»")
    db.commit()
    db.refresh(r)
    return r


def list_reports(db: Session, user: User, project_id: int | None = None) -> list[Report]:
    stmt = select(Report).where(Report.owner_id == user.id)
    if project_id is not None:
        stmt = stmt.where(Report.project_id == project_id)
    return list(db.scalars(stmt.order_by(Report.updated_at.desc())))


def get_report(db: Session, user: User, report_id: int) -> Report:
    r = db.get(Report, report_id)
    if r is None or r.owner_id != user.id:
        raise NotFoundError("Rapporto non trovato.")
    return r


def _to_draft(r: Report) -> None:
    # Ogni modifica a un rapporto approvato lo riporta in bozza: l'approvazione vale per il contenuto approvato.
    r.status = "draft"


def update_report(db: Session, user: User, report_id: int, data: ReportUpdate) -> Report:
    r = get_report(db, user, report_id)
    changes = data.model_dump(exclude_unset=True)
    if "project_id" in changes:
        _project(db, user, changes["project_id"])
    if changes.get("source_ids") is not None:
        ids = list(dict.fromkeys(changes["source_ids"]))
        found = set(db.scalars(select(Source.id).where(Source.owner_id == user.id, Source.id.in_(ids))))
        if set(ids) - found:
            raise ValidationFailedError(f"Fonti inesistenti: {sorted(set(ids) - found)}")
        changes["source_ids"] = ids
    for k, v in changes.items():
        setattr(r, k, v)
    _to_draft(r)
    db.commit()
    db.refresh(r)
    return r


def update_section(db: Session, user: User, report_id: int, section_id: int, data: SectionIn) -> Report:
    r = get_report(db, user, report_id)
    sec = next((s for s in r.sections if s.id == section_id), None)
    if sec is None:
        raise NotFoundError("Sezione non trovata.")
    if data.title is not None:
        if sec.key != "chapter":
            raise ValidationFailedError("Il titolo delle sezioni obbligatorie non è modificabile.")
        sec.title = data.title
    if data.body is not None:
        sec.body = data.body
    if data.embeds is not None:
        sec.embeds = [e.model_dump() for e in data.embeds]
    _to_draft(r)
    db.commit()
    db.refresh(r)
    return r


def add_chapter(db: Session, user: User, report_id: int, data: ChapterIn) -> Report:
    r = get_report(db, user, report_id)
    anchor = next((s for s in r.sections if s.key == data.after_key or str(s.id) == data.after_key), None)
    if anchor is None:
        raise ValidationFailedError("Sezione di riferimento inesistente.")
    for s in r.sections:
        if s.ordinal > anchor.ordinal:
            s.ordinal += 1
    r.sections.append(ReportSection(ordinal=anchor.ordinal + 1, key="chapter", title=data.title, body="", embeds=[]))
    _to_draft(r)
    db.commit()
    db.refresh(r)
    r.sections.sort(key=lambda s: s.ordinal)
    return r


def delete_chapter(db: Session, user: User, report_id: int, section_id: int) -> Report:
    r = get_report(db, user, report_id)
    sec = next((s for s in r.sections if s.id == section_id), None)
    if sec is None or sec.key != "chapter":
        raise ValidationFailedError("Si possono eliminare solo i capitoli aggiuntivi, non le sezioni obbligatorie.")
    r.sections.remove(sec)
    for i, s in enumerate(sorted(r.sections, key=lambda x: x.ordinal)):
        s.ordinal = i
    _to_draft(r)
    db.commit()
    db.refresh(r)
    return r


def move_chapter(db: Session, user: User, report_id: int, section_id: int, direction: int) -> Report:
    r = get_report(db, user, report_id)
    ordered = sorted(r.sections, key=lambda s: s.ordinal)
    i = next((k for k, s in enumerate(ordered) if s.id == section_id), None)
    if i is None or ordered[i].key != "chapter":
        raise ValidationFailedError("Solo i capitoli aggiuntivi possono essere spostati.")
    j = i + direction
    if 0 <= j < len(ordered):
        ordered[i].ordinal, ordered[j].ordinal = ordered[j].ordinal, ordered[i].ordinal
    _to_draft(r)
    db.commit()
    db.refresh(r)
    return r


def delete_report(db: Session, user: User, report_id: int, confirm: bool) -> None:
    r = get_report(db, user, report_id)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un rapporto richiede conferma (confirm=true).")
    db.delete(r)
    activity.record(db, user=user, actor="user", action="report.delete", entity_type="report", entity_id=report_id, summary=f"Eliminato il rapporto «{r.title}»")
    db.commit()


# --- Verifica e bibliografia -------------------------------------------------------------------


def _bibliography(db: Session, user: User, r: Report) -> tuple[list[Source], list[int], dict[int, int]]:
    ordered = sorted(r.sections, key=lambda s: s.ordinal)
    cited = citations.cited_ids([s.body for s in ordered])
    sources = {s.id: s for s in db.scalars(select(Source).where(Source.owner_id == user.id, Source.id.in_(cited + list(r.source_ids))))}
    invalid = [i for i in cited if i not in sources]
    order = [i for i in cited if i in sources] + [i for i in r.source_ids if i in sources and i not in cited]
    numbering = {sid: n for n, sid in enumerate(order, start=1)}
    return [sources[i] for i in order], invalid, numbering


def check(db: Session, user: User, report_id: int) -> ReportCheck:
    r = get_report(db, user, report_id)
    bib, invalid, numbering = _bibliography(db, user, r)
    empty = [s.title for s in r.sections if s.key != "chapter" and not s.body.strip()]
    unverified = [{"id": s.id, "citation": format_citation(s), "status": VERIFICATION_LABEL[s.verification_status]} for s in bib if s.verification_status not in VERIFIED]
    problems = []
    for s in r.sections:
        for e in s.embeds:
            if e["type"] == "series" and not _owned(db, Series, e["series_id"], user):
                problems.append(f"«{s.title}»: serie {e['series_id']} inesistente")
            if e["type"] == "simulation" and not _owned(db, SimulationRun, e["simulation_id"], user):
                problems.append(f"«{s.title}»: simulazione {e['simulation_id']} inesistente")
    warnings = []
    if r.contains_ai_text:
        warnings.append("Il rapporto contiene testo generato o estratto automaticamente: rivedilo prima dell'approvazione.")
    if not bib:
        warnings.append("Nessuna fonte in bibliografia.")
    return ReportCheck(ready=not (empty or invalid or problems), empty_sections=empty, invalid_citations=invalid, unverified_sources=unverified,
                       cited_sources=len([1 for s in bib if s.id in numbering]), bibliography_size=len(bib), embed_problems=problems, warnings=warnings)


def _owned(db: Session, model, oid: int, user: User):
    o = db.get(model, oid)
    return o if o is not None and o.owner_id == user.id else None


def set_status(db: Session, user: User, report_id: int, status: str) -> Report:
    r = get_report(db, user, report_id)
    if status == "approved":
        c = check(db, user, report_id)
        if not c.ready:
            raise ValidationFailedError("Il rapporto non può essere approvato: completa le sezioni e correggi citazioni e allegati.", details=c.model_dump())
    r.status = status
    activity.record(db, user=user, actor="user", action=f"report.{status}", entity_type="report", entity_id=r.id,
                    summary=f"Rapporto «{r.title}» {'approvato' if status == 'approved' else 'riportato in bozza'}")
    db.commit()
    db.refresh(r)
    return r


# --- Vista ed esportazione ----------------------------------------------------------------------


def _figure(db: Session, user: User, e: dict) -> export.Figure:
    if e["type"] == "series":
        s = _owned(db, Series, e["series_id"], user)
        if s is None:
            return export.Figure(caption=e.get("caption") or "Serie non disponibile", note="serie eliminata o inesistente")
        obs = [o for o in s.observations]
        png = charts.line_chart(s.name, [o.date[:7] if s.frequency != "A" else o.date[:4] for o in obs], {s.name: [o.value for o in obs]}, s.unit, s.source_label)
        return export.Figure(caption=e.get("caption") or s.name, png=png,
                             note=f"Fonte: {s.source_label}; unità: {s.unit or 'n.d.'}; ultimo aggiornamento dichiarato: {s.source_last_updated or 'n.d.'}")
    sim = _owned(db, SimulationRun, e["simulation_id"], user)
    if sim is None:
        return export.Figure(caption=e.get("caption") or "Simulazione non disponibile", note="simulazione eliminata o inesistente")
    res = sim.result.get("results", {})
    label = sim.result.get("label", "")
    png = None
    if "fan" in res:
        fan = res["fan"]
        png = charts.line_chart(sim.title, [str(f["t"]) for f in fan], {"95° perc.": [f["p95"] for f in fan], "Mediana": [f["p50"] for f in fan], "5° perc.": [f["p5"] for f in fan]})
    elif sim.kind == "debt":
        series = {"Base": res["baseline"]["debt"]}
        if "rate_shock" in res:
            series["Shock tassi"] = res["rate_shock"]["debt"]
        if "crisis" in res:
            series["Crisi"] = res["crisis"]["debt"]
        png = charts.line_chart(sim.title, [str(y) for y in res["years"]], series, "% PIL")
    elif sim.kind == "backtest":
        eq = res["equity"]
        png = charts.line_chart(sim.title, [x["date"][:7] for x in eq], {"Strategia": [x["strategy"] for x in eq], "Buy & hold": [x["benchmark"] for x in eq]})
    return export.Figure(caption=e.get("caption") or sim.title, png=png, note=f"{label} Metodo: {sim.result.get('method', '')}")


def build_view(db: Session, user: User, report_id: int) -> export.ReportView:
    r = get_report(db, user, report_id)
    bib, invalid, numbering = _bibliography(db, user, r)
    sections = []
    for s in sorted(r.sections, key=lambda x: x.ordinal):
        figs = [_figure(db, user, e) for e in s.embeds if e["type"] in ("series", "simulation")]
        tables = [export.Table(e.get("caption", ""), e["columns"], e["rows"]) for e in s.embeds if e["type"] == "table"]
        sections.append(export.SectionView(s.title, export.paragraphs(citations.render(s.body, numbering)), figs, tables))
    notices = []
    if r.status != "approved":
        notices.append("BOZZA: rapporto non ancora approvato dall'autore.")
    if r.contains_ai_text:
        notices.append("Parti del testo sono state generate o estratte automaticamente da NEXUS: verificare prima dell'uso.")
    if invalid:
        notices.append(f"Citazioni non valide (fonti inesistenti): {invalid}.")
    unv = sum(1 for s in bib if s.verification_status not in VERIFIED)
    if unv:
        notices.append(f"{unv} fonti in bibliografia non sono verificate (segnalate).")
    entries = [export.BibEntry(numbering[s.id], format_citation(s), s.verification_status in VERIFIED, VERIFICATION_LABEL[s.verification_status]) for s in bib]
    return export.ReportView(r.title, r.subtitle, r.author, "Approvato" if r.status == "approved" else "Bozza",
                             datetime.now().strftime("%d/%m/%Y %H:%M"), sections, entries, notices)


def export_report(db: Session, user: User, report_id: int, fmt: str) -> tuple[bytes, str]:
    v = build_view(db, user, report_id)
    data = export.to_pdf(v) if fmt == "pdf" else export.to_docx(v)
    activity.record(db, user=user, actor="user", action=f"report.export_{fmt}", entity_type="report", entity_id=report_id,
                    summary=f"Esportato «{v.title}» in {fmt.upper()} ({v.status})")
    db.commit()
    return data, v.title


# --- Da una ricerca della War Room ------------------------------------------------------------------


CLAIM_LABEL = {"documented_fact": "Fatto documentato", "interpretation": "Interpretazione", "hypothesis": "Ipotesi", "estimate": "Stima", "missing": "Dato mancante"}


def from_research_run(db: Session, user: User, run_id: int) -> Report:
    run = db.get(ResearchRun, run_id)
    if run is None or run.owner_id != user.id:
        raise NotFoundError("Ricerca non trovata.")
    if run.status != "approved":
        raise ValidationFailedError("Solo una ricerca approvata può diventare un rapporto.")
    ev = {e["id"]: e for e in run.evidence}
    # Le evidenze da documenti collegati a una scheda bibliografica diventano citazioni verificabili.
    source_of: dict[str, int] = {}
    for e in run.evidence:
        if e["kind"] == "passage":
            d = db.get(Document, e["ref"].get("document_id"))
            if d and d.source_id:
                source_of[e["id"]] = d.source_id

    def cite(ids) -> str:
        parts = []
        for i in ids:
            key = i if isinstance(i, str) else next((k for k, e in ev.items() if e["ref"].get("chunk_id") == i), None)
            if key in source_of:
                parts.append(f"[@{source_of[key]}]")
            elif key in ev:
                parts.append(f"({ev[key]['label']})")
        return " ".join(parts)

    res = run.result
    claims = res.get("claims", [])
    r = create_report(db, user, ReportCreate(title=f"Ricerca: {run.question[:280]}", project_id=run.project_id), origin=f"research_run:{run.id}")
    r.contains_ai_text = run.mode == "ai"
    body = {
        "abstract": (res.get("abstract") or "") + ("\n\n[Abstract generato da modello AI]" if run.mode == "ai" and res.get("abstract") else ""),
        "introduction": f"Domanda di ricerca: {run.question}",
        "methodology": "\n".join([
            f"- Modalità: {'AI (' + run.provider + (', ' + run.model if run.model else '') + ')' if run.mode == 'ai' else 'motore locale, senza modelli AI'}",
            f"- Pianificazione: {run.plan.get('method', 'n.d.')}; query: {', '.join(run.plan.get('search_queries', []))}",
            f"- Evidenze raccolte: {len(run.evidence)} (documenti, eventi d'archivio, serie)",
            f"- Agenti: " + ", ".join(f"{s.agent} ({'non eseguito' if s.status == 'skipped' else s.executor})" for s in run.steps),
            f"- Approvata dall'utente il {run.decided_at:%d/%m/%Y}" if run.decided_at else "- Approvazione: n.d.",
        ]),
        "analysis": "\n\n".join(f"[{CLAIM_LABEL.get(c['type'], c['type'])}] {c['text']} {cite(c.get('evidence', []))}".strip()
                                for c in claims if c["type"] != "missing"),
        "evidence": "\n".join(f"- {e['id']}: {e['label']} — {e['source']}" + (f" {cite([e['id']])}" if e["id"] in source_of else "") for e in run.evidence),
        "counterarguments": "\n".join(f"- {x}" for x in res.get("limitations", [])),
        "conclusions": "",
        "limitations": "\n".join(f"- [Dato mancante] {c['text']}" for c in claims if c["type"] == "missing"),
    }
    for s in r.sections:
        s.body = body.get(s.key, "")
    db.commit()
    db.refresh(r)
    return r


# --- Appunti ------------------------------------------------------------------------------------------------


def _note_refs(db: Session, user: User, data: NoteIn) -> None:
    _project(db, user, data.project_id)
    if data.source_id is not None and not _owned(db, Source, data.source_id, user):
        raise ValidationFailedError("Fonte inesistente.")
    if data.document_id is not None and not _owned(db, Document, data.document_id, user):
        raise ValidationFailedError("Documento inesistente.")


def list_notes(db: Session, user: User, project_id: int | None = None) -> list[Note]:
    stmt = select(Note).where(Note.owner_id == user.id)
    if project_id is not None:
        stmt = stmt.where(Note.project_id == project_id)
    return list(db.scalars(stmt.order_by(Note.updated_at.desc())))


def create_note(db: Session, user: User, data: NoteIn) -> Note:
    _note_refs(db, user, data)
    n = Note(owner_id=user.id, **data.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def update_note(db: Session, user: User, note_id: int, data: NoteIn) -> Note:
    n = _owned(db, Note, note_id, user)
    if n is None:
        raise NotFoundError("Appunto non trovato.")
    _note_refs(db, user, data)
    for k, v in data.model_dump().items():
        setattr(n, k, v)
    db.commit()
    db.refresh(n)
    return n


def delete_note(db: Session, user: User, note_id: int, confirm: bool) -> None:
    n = _owned(db, Note, note_id, user)
    if n is None:
        raise NotFoundError("Appunto non trovato.")
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un appunto richiede conferma (confirm=true).")
    db.delete(n)
    db.commit()
