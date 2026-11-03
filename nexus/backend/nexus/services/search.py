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
from ..models import Project, SearchQuery, User

UNAVAILABLE_SCOPES = [
    "documenti (Fase 2)",
    "eventi storici (Fase 3)",
    "entità del Knowledge Graph (Fase 3)",
    "serie finanziarie (Fase 4)",
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
        searched_scopes=["progetti", "catalogo moduli"],
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
