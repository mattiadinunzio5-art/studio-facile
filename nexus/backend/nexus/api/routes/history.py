from typing import Annotated

from fastapi import APIRouter, Query, status

from ...services import graph as graph_svc
from ...services import history as svc
from ...services import timemachine
from ..deps import DB, CurrentUser
from ..schemas_history import (
    Category,
    EventIn,
    EventLinkIn,
    EventOut,
    EventSourceLinkIn,
    KnowledgeIn,
    Reliability,
    RelationOut,
    TimelineOut,
)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/events", response_model=list[EventOut])
def list_events(
    db: DB, user: CurrentUser, q: str | None = Query(None, max_length=200), category: Category | None = None,
    country: str | None = Query(None, max_length=120), from_year: int | None = None, to_year: int | None = None,
    reliability: Reliability | None = None,
):
    return [svc.to_out(db, e) for e in svc.list_events(db, user, q=q, category=category, country=country,
                                                       from_year=from_year, to_year=to_year, reliability=reliability)]


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(data: EventIn, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.create_event(db, user, data))


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.get_event(db, user, event_id))


@router.put("/events/{event_id}", response_model=EventOut)
def update_event(event_id: int, data: EventIn, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.update_event(db, user, event_id, data))


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_event(db, user, event_id, confirm)


@router.post("/events/{event_id}/sources", response_model=EventOut)
def link_source(event_id: int, data: EventSourceLinkIn, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.link_source(db, user, event_id, data.source_id, data.pages, data.note))


@router.delete("/events/{event_id}/sources/{source_id}", response_model=EventOut)
def unlink_source(event_id: int, source_id: int, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.unlink_source(db, user, event_id, source_id))


@router.post("/events/{event_id}/knowledge", response_model=EventOut, summary="Aggiunge un'informazione datata (per la Time Machine)")
def add_knowledge(event_id: int, data: KnowledgeIn, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.add_knowledge(db, user, event_id, data))


@router.delete("/events/{event_id}/knowledge/{item_id}", response_model=EventOut)
def delete_knowledge(event_id: int, item_id: int, db: DB, user: CurrentUser):
    return svc.to_out(db, svc.delete_knowledge(db, user, event_id, item_id))


@router.post("/events/{event_id}/links", response_model=RelationOut, status_code=status.HTTP_201_CREATED,
             summary="Collega due eventi (crea una relazione nel Knowledge Graph)")
def link_events(event_id: int, data: EventLinkIn, db: DB, user: CurrentUser):
    return graph_svc.relation_out(db, svc.link_events(db, user, event_id, data))


@router.get("/timeline", response_model=TimelineOut, summary="Time Machine con filtro anti-senno-di-poi")
def timeline(
    db: DB, user: CurrentUser,
    as_of_year: Annotated[int | None, Query(ge=-10000, le=2200)] = None,
    hindsight: bool = False,
    country: str | None = Query(None, max_length=120),
    category: Category | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    event_id: int | None = None,
):
    return timemachine.timeline(db, user, as_of_year=as_of_year, hindsight=hindsight, country=country,
                                category=category, from_year=from_year, to_year=to_year, event_id=event_id)
