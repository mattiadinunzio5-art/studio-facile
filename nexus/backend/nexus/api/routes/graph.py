from fastapi import APIRouter, Query, status

from ...services import graph as svc
from ..deps import DB, CurrentUser
from ..schemas_history import EntityIn, EntityOut, EntityType, GraphOut, PathOut, Provenance, RelationIn, RelationOut, RelationType

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


@router.get("", response_model=GraphOut, summary="Esplora il grafo (con layout calcolato da NetworkX)")
def explore(
    db: DB, user: CurrentUser, focus: int | None = None, depth: int = Query(2, ge=1, le=4),
    relation_types: list[RelationType] = Query(default=[]), provenance: list[Provenance] = Query(default=[]),
    entity_types: list[EntityType] = Query(default=[]),
):
    return svc.explore(db, user, focus=focus, depth=depth, relation_types=relation_types or None,
                       provenance=provenance or None, entity_types=entity_types or None)


@router.get("/path", response_model=PathOut, summary="Percorso più breve tra due entità")
def path(db: DB, user: CurrentUser, source: int, target: int):
    return svc.path(db, user, source, target)


@router.get("/entities", response_model=list[EntityOut])
def list_entities(db: DB, user: CurrentUser, q: str | None = Query(None, max_length=200), entity_type: EntityType | None = None):
    return svc.list_entities(db, user, q, entity_type)


@router.post("/entities", response_model=EntityOut, status_code=status.HTTP_201_CREATED)
def create_entity(data: EntityIn, db: DB, user: CurrentUser):
    return svc.create_entity(db, user, data)


@router.get("/entities/{entity_id}", response_model=EntityOut)
def get_entity(entity_id: int, db: DB, user: CurrentUser):
    return svc.get_entity(db, user, entity_id)


@router.put("/entities/{entity_id}", response_model=EntityOut)
def update_entity(entity_id: int, data: EntityIn, db: DB, user: CurrentUser):
    return svc.update_entity(db, user, entity_id, data)


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_entity(db, user, entity_id, confirm)


@router.get("/entities/{entity_id}/relations", response_model=list[RelationOut])
def entity_relations(entity_id: int, db: DB, user: CurrentUser):
    svc.get_entity(db, user, entity_id)
    return [svc.relation_out(db, r) for r in svc.relations_of(db, user, entity_id)]


@router.post("/relations", response_model=RelationOut, status_code=status.HTTP_201_CREATED)
def create_relation(data: RelationIn, db: DB, user: CurrentUser):
    return svc.relation_out(db, svc.create_relation(db, user, data))


@router.delete("/relations/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relation(relation_id: int, db: DB, user: CurrentUser) -> None:
    svc.delete_relation(db, user, relation_id)
