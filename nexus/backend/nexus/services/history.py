"""Archivio degli eventi storici."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..api.schemas_history import EventIn, EventLinkIn, EventOut, EventSourceOut, KnowledgeIn, KnowledgeOut, RelationIn
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..history import dates
from ..models import Entity, EventSource, HistoricalEvent, KnowledgeItem, Source, User
from ..research.citations import format_citation
from . import activity, graph


def to_out(db: Session, e: HistoricalEvent) -> EventOut:
    out = EventOut.model_validate(e)
    out.date_label = dates.fmt_range(e.start_year, e.start_month, e.start_day, e.end_year, e.end_month, e.end_day)
    srcs = []
    for link in e.source_links:
        s = db.get(Source, link.source_id)
        if s:
            srcs.append(EventSourceOut(source_id=s.id, citation=format_citation(s), verification_status=s.verification_status, pages=link.pages, note=link.note))
    out.sources = srcs
    out.knowledge = [KnowledgeOut.model_validate(k) for k in e.knowledge]
    ent = db.scalar(select(Entity.id).where(Entity.event_id == e.id))
    out.entity_id = ent
    if not srcs:
        out.source_warning = "Nessuna fonte bibliografica collegata: le informazioni non sono verificabili."
    elif not any(s.verification_status in ("verified_user", "verified_registry") for s in srcs):
        out.source_warning = "Le fonti collegate non sono ancora verificate."
    return out


def _source(db: Session, user: User, source_id: int | None) -> None:
    if source_id is None:
        return
    s = db.get(Source, source_id)
    if s is None or s.owner_id != user.id:
        raise ValidationFailedError("Fonte inesistente.")


def list_events(
    db: Session, user: User, *, q: str | None = None, category: str | None = None, country: str | None = None,
    from_year: int | None = None, to_year: int | None = None, reliability: str | None = None, limit: int = 500,
) -> list[HistoricalEvent]:
    stmt = select(HistoricalEvent).where(HistoricalEvent.owner_id == user.id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(HistoricalEvent.title.ilike(like), HistoricalEvent.description.ilike(like)))
    if from_year is not None:
        stmt = stmt.where(or_(HistoricalEvent.end_year >= from_year, HistoricalEvent.start_year >= from_year))
    if to_year is not None:
        stmt = stmt.where(HistoricalEvent.start_year <= to_year)
    if reliability:
        stmt = stmt.where(HistoricalEvent.reliability == reliability)
    stmt = stmt.order_by(HistoricalEvent.start_year, HistoricalEvent.start_month, HistoricalEvent.start_day)
    events = list(db.scalars(stmt))
    # Filtri su liste JSON applicati in Python (portabile tra SQLite e PostgreSQL).
    if category:
        events = [e for e in events if category in e.categories]
    if country:
        c = country.lower()
        events = [e for e in events if any(c == x.lower() for x in e.countries) or c in e.region.lower()]
    return events[:limit]


def get_event(db: Session, user: User, event_id: int) -> HistoricalEvent:
    e = db.get(HistoricalEvent, event_id)
    if e is None or e.owner_id != user.id:
        raise NotFoundError("Evento non trovato.")
    return e


def create_event(db: Session, user: User, data: EventIn, is_demo: bool = False) -> HistoricalEvent:
    e = HistoricalEvent(owner_id=user.id, is_demo=is_demo, **data.model_dump())
    db.add(e)
    db.flush()
    # Ogni evento è anche un nodo del Knowledge Graph.
    db.add(Entity(owner_id=user.id, entity_type="event", name=e.title, description=e.description[:2000],
                  start_year=e.start_year, end_year=e.end_year, event_id=e.id, is_demo=is_demo))
    activity.record(db, user=user, actor="user", action="event.create", entity_type="event", entity_id=e.id,
                    summary=f"Creato l'evento «{e.title}»" + (" (DEMO)" if is_demo else ""))
    db.commit()
    db.refresh(e)
    return e


def update_event(db: Session, user: User, event_id: int, data: EventIn) -> HistoricalEvent:
    e = get_event(db, user, event_id)
    for k, v in data.model_dump().items():
        setattr(e, k, v)
    ent = db.scalar(select(Entity).where(Entity.event_id == e.id))
    if ent:
        ent.name, ent.start_year, ent.end_year = e.title, e.start_year, e.end_year
        ent.description = e.description[:2000]
    activity.record(db, user=user, actor="user", action="event.update", entity_type="event", entity_id=e.id,
                    summary=f"Modificato l'evento «{e.title}»")
    db.commit()
    db.refresh(e)
    return e


def delete_event(db: Session, user: User, event_id: int, confirm: bool) -> None:
    e = get_event(db, user, event_id)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un evento (e le sue relazioni nel grafo) richiede conferma (confirm=true).")
    title = e.title
    db.delete(e)
    activity.record(db, user=user, actor="user", action="event.delete", entity_type="event", entity_id=event_id,
                    summary=f"Eliminato l'evento «{title}»")
    db.commit()


def link_source(db: Session, user: User, event_id: int, source_id: int, pages: str, note: str) -> HistoricalEvent:
    e = get_event(db, user, event_id)
    _source(db, user, source_id)
    if any(link.source_id == source_id for link in e.source_links):
        raise ValidationFailedError("Fonte già collegata a questo evento.")
    e.source_links.append(EventSource(source_id=source_id, pages=pages, note=note))
    activity.record(db, user=user, actor="user", action="event.source", entity_type="event", entity_id=e.id,
                    summary=f"Collegata una fonte all'evento «{e.title}»")
    db.commit()
    db.refresh(e)
    return e


def unlink_source(db: Session, user: User, event_id: int, source_id: int) -> HistoricalEvent:
    e = get_event(db, user, event_id)
    e.source_links = [link for link in e.source_links if link.source_id != source_id]
    db.commit()
    db.refresh(e)
    return e


def add_knowledge(db: Session, user: User, event_id: int, data: KnowledgeIn) -> HistoricalEvent:
    e = get_event(db, user, event_id)
    _source(db, user, data.source_id)
    if data.kind == "contemporary" and data.known_since_year < e.start_year:
        raise ValidationFailedError("Un'informazione contemporanea non può essere nota prima dell'inizio dell'evento.")
    e.knowledge.append(KnowledgeItem(**data.model_dump()))
    db.commit()
    db.refresh(e)
    return e


def delete_knowledge(db: Session, user: User, event_id: int, item_id: int) -> HistoricalEvent:
    e = get_event(db, user, event_id)
    e.knowledge = [k for k in e.knowledge if k.id != item_id]
    db.commit()
    db.refresh(e)
    return e


def link_events(db: Session, user: User, event_id: int, data: EventLinkIn):
    src = get_event(db, user, event_id)
    tgt = get_event(db, user, data.target_event_id)
    a = db.scalar(select(Entity).where(Entity.event_id == src.id))
    b = db.scalar(select(Entity).where(Entity.event_id == tgt.id))
    rel = RelationIn(
        source_entity_id=a.id, target_entity_id=b.id, relation_type=data.relation_type, provenance=data.provenance,
        source_id=data.source_id, chunk_id=data.chunk_id, evidence_note=data.evidence_note, confidence=data.confidence,
    )
    return graph.create_relation(db, user, rel)
