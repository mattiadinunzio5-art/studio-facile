"""Ricerca globale.

In Fase 1 cerca (testo, case-insensitive) nei progetti dell'utente e nel
catalogo dei moduli. La risposta dichiara quali ambiti non sono ancora
ricercabili, invece di restituire risultati fittizi.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..api.schemas import SearchHit, SearchResultOut
from ..core.modules import MODULES
from ..models import Document, Entity, HistoricalEvent, Project, SearchQuery, Series, User
from ..research import index

UNAVAILABLE_SCOPES = [
    "rapporti (Fase 7)",
]


def _snippet(text: str, query: str, width: int = 140) -> str:
    if not text:
        return ""
    idx = text.lower().find(query.lower())
    if idx < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, idx - width // 3)
    end = min(len(text), start + width)
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def _escape_like(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def search(db: Session, user: User, query: str, limit: int = 25) -> SearchResultOut:
    pattern = f"%{_escape_like(query)}%"
    projects = db.scalars(
        select(Project)
        .where(
            Project.owner_id == user.id,
            or_(
                Project.title.ilike(pattern, escape="\\"),
                Project.description.ilike(pattern, escape="\\"),
            ),
        )
        .order_by(Project.updated_at.desc())
        .limit(limit)
    )
    hits = [
        SearchHit(
            type="project",
            id=str(p.id),
            title=p.title + (" [DEMO]" if p.is_demo else ""),
            snippet=_snippet(p.description, query),
            url=f"/projects?id={p.id}",
        )
        for p in projects
    ]
    doc_ids_seen: set[int] = set()
    for d in db.scalars(
        select(Document).where(Document.owner_id == user.id, Document.title.ilike(pattern, escape="\\")).limit(limit)
    ):
        doc_ids_seen.add(d.id)
        hits.append(SearchHit(type="document", id=str(d.id), title=d.title, snippet=f"{d.kind.upper()} · {d.chunk_count} segmenti", url=f"/documents/{d.id}"))
    for cid, _ in index.text_search(db, user.id, query, 10):
        from ..models import DocumentChunk

        c = db.get(DocumentChunk, cid)
        if c is None or c.document_id in doc_ids_seen:
            continue
        doc_ids_seen.add(c.document_id)
        hits.append(
            SearchHit(type="document", id=str(c.document_id), title=c.document.title + (f" — {c.locator}" if c.locator else ""),
                      snippet=_snippet(c.text, query), url=f"/documents/{c.document_id}")
        )
    for e in db.scalars(
        select(HistoricalEvent).where(
            HistoricalEvent.owner_id == user.id,
            or_(HistoricalEvent.title.ilike(pattern, escape="\\"), HistoricalEvent.description.ilike(pattern, escape="\\")),
        ).limit(limit)
    ):
        hits.append(SearchHit(type="event", id=str(e.id), title=e.title + (" [DEMO]" if e.is_demo else ""),
                              snippet=_snippet(e.description, query), url=f"/history/events/{e.id}"))
    for ent in db.scalars(
        select(Entity).where(Entity.owner_id == user.id, Entity.event_id.is_(None), Entity.name.ilike(pattern, escape="\\")).limit(limit)
    ):
        hits.append(SearchHit(type="entity", id=str(ent.id), title=ent.name, snippet=ent.entity_type, url=f"/graph?focus={ent.id}"))
    for se in db.scalars(select(Series).where(Series.owner_id == user.id, Series.name.ilike(pattern, escape="\\")).limit(limit)):
        hits.append(SearchHit(type="series", id=str(se.id), title=se.name, snippet=se.source_label, url=f"/financial/series/{se.id}"))
    q = query.lower()
    for m in MODULES:
        if q in m.name.lower() or q in m.summary.lower():
            hits.append(
                SearchHit(
                    type="module",
                    id=m.id,
                    title=f"{m.code} · {m.name}",
                    snippet=m.summary,
                    url=f"/modules/{m.id}",
                )
            )

    db.add(SearchQuery(user_id=user.id, query=query, results_count=len(hits)))
    db.commit()
    return SearchResultOut(
        query=query,
        hits=hits,
        searched_scopes=["progetti", "documenti", "eventi storici", "entità", "serie", "catalogo moduli"],
        unavailable_scopes=UNAVAILABLE_SCOPES,
    )


def recent_queries(db: Session, user: User, limit: int = 8) -> list[SearchQuery]:
    """Ultime ricerche distinte (la ripetizione di una query mostra solo la più recente)."""
    rows = db.scalars(
        select(SearchQuery)
        .where(SearchQuery.user_id == user.id)
        .order_by(SearchQuery.created_at.desc(), SearchQuery.id.desc())
        .limit(limit * 10)
    )
    seen: set[str] = set()
    result: list[SearchQuery] = []
    for row in rows:
        key = row.query.casefold()
        if key not in seen:
            seen.add(key)
            result.append(row)
        if len(result) == limit:
            break
    return result
