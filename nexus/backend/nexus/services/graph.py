"""Knowledge Graph: entità, relazioni con provenienza, esplorazione con NetworkX."""

from __future__ import annotations

import networkx as nx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..api.schemas_history import EntityIn, GraphNode, GraphOut, PathOut, RelationIn, RelationOut
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..models import Document, DocumentChunk, Entity, Relation, Source, User
from ..research.citations import format_citation
from . import activity

PROVENANCE_LABEL = {
    "sourced": "Documentata",
    "user_hypothesis": "Ipotesi dell'utente",
    "ai_hypothesis": "Ipotesi generata dall'AI — da verificare",
}


def relation_out(db: Session, r: Relation) -> RelationOut:
    out = RelationOut.model_validate(r)
    if r.source_id:
        s = db.get(Source, r.source_id)
        out.evidence_label = format_citation(s) if s else "Fonte eliminata"
    elif r.chunk_id:
        c = db.get(DocumentChunk, r.chunk_id)
        out.evidence_label = f"{c.document.title}, {c.locator}" if c else "Passaggio eliminato"
    else:
        out.evidence_label = PROVENANCE_LABEL[r.provenance]
    return out


def get_entity(db: Session, user: User, entity_id: int) -> Entity:
    e = db.get(Entity, entity_id)
    if e is None or e.owner_id != user.id:
        raise NotFoundError("Entità non trovata.")
    return e


def list_entities(db: Session, user: User, q: str | None = None, entity_type: str | None = None, limit: int = 500) -> list[Entity]:
    stmt = select(Entity).where(Entity.owner_id == user.id)
    if q:
        stmt = stmt.where(Entity.name.ilike(f"%{q}%"))
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    return list(db.scalars(stmt.order_by(Entity.name).limit(limit)))


def create_entity(db: Session, user: User, data: EntityIn, is_demo: bool = False) -> Entity:
    if data.entity_type == "event":
        raise ValidationFailedError("Le entità di tipo evento si creano dall'archivio storico.")
    if data.document_id is not None:
        d = db.get(Document, data.document_id)
        if d is None or d.owner_id != user.id:
            raise ValidationFailedError("Documento inesistente.")
    e = Entity(owner_id=user.id, is_demo=is_demo, **data.model_dump())
    db.add(e)
    db.flush()
    activity.record(db, user=user, actor="user", action="entity.create", entity_type="entity", entity_id=e.id,
                    summary=f"Creata l'entità «{e.name}» ({e.entity_type})")
    db.commit()
    db.refresh(e)
    return e


def update_entity(db: Session, user: User, entity_id: int, data: EntityIn) -> Entity:
    e = get_entity(db, user, entity_id)
    if e.event_id is not None:
        raise ValidationFailedError("Questa entità rappresenta un evento: modificala dalla scheda evento.")
    for k, v in data.model_dump().items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return e


def delete_entity(db: Session, user: User, entity_id: int, confirm: bool) -> None:
    e = get_entity(db, user, entity_id)
    if e.event_id is not None:
        raise ValidationFailedError("Questa entità rappresenta un evento: eliminala dall'archivio storico.")
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un'entità e le sue relazioni richiede conferma (confirm=true).")
    db.delete(e)
    activity.record(db, user=user, actor="user", action="entity.delete", entity_type="entity", entity_id=entity_id,
                    summary=f"Eliminata l'entità «{e.name}»")
    db.commit()


def _check_evidence(db: Session, user: User, source_id: int | None, chunk_id: int | None) -> None:
    if source_id is not None:
        s = db.get(Source, source_id)
        if s is None or s.owner_id != user.id:
            raise ValidationFailedError("Fonte inesistente.")
    if chunk_id is not None:
        c = db.get(DocumentChunk, chunk_id)
        if c is None or c.owner_id != user.id:
            raise ValidationFailedError("Passaggio di documento inesistente.")


def create_relation(db: Session, user: User, data: RelationIn, *, ai_run_id: int | None = None, provenance_override: str | None = None) -> Relation:
    get_entity(db, user, data.source_entity_id)
    get_entity(db, user, data.target_entity_id)
    _check_evidence(db, user, data.source_id, data.chunk_id)
    values = data.model_dump()
    if provenance_override:
        values["provenance"] = provenance_override
    dup = db.scalar(
        select(Relation).where(
            Relation.owner_id == user.id, Relation.source_entity_id == data.source_entity_id,
            Relation.target_entity_id == data.target_entity_id, Relation.relation_type == data.relation_type,
            Relation.provenance == values["provenance"],
        )
    )
    if dup:
        raise ValidationFailedError("Relazione già presente.")
    r = Relation(owner_id=user.id, ai_run_id=ai_run_id, **values)
    db.add(r)
    db.flush()
    activity.record(db, user=user, actor="ai" if ai_run_id else "user", action="relation.create", entity_type="relation", entity_id=r.id,
                    summary=f"Nuova relazione «{r.relation_type}» ({PROVENANCE_LABEL[r.provenance]})")
    db.commit()
    db.refresh(r)
    return r


def delete_relation(db: Session, user: User, relation_id: int) -> None:
    r = db.get(Relation, relation_id)
    if r is None or r.owner_id != user.id:
        raise NotFoundError("Relazione non trovata.")
    db.delete(r)
    activity.record(db, user=user, actor="user", action="relation.delete", entity_type="relation", entity_id=relation_id,
                    summary="Eliminata una relazione del grafo")
    db.commit()


def relations_of(db: Session, user: User, entity_id: int) -> list[Relation]:
    return list(
        db.scalars(
            select(Relation).where(
                Relation.owner_id == user.id,
                or_(Relation.source_entity_id == entity_id, Relation.target_entity_id == entity_id),
            )
        )
    )


def _graph(db: Session, user: User, relation_types: list[str] | None, provenance: list[str] | None):
    g = nx.MultiDiGraph()
    entities = {e.id: e for e in db.scalars(select(Entity).where(Entity.owner_id == user.id))}
    for e in entities.values():
        g.add_node(e.id)
    stmt = select(Relation).where(Relation.owner_id == user.id)
    if relation_types:
        stmt = stmt.where(Relation.relation_type.in_(relation_types))
    if provenance:
        stmt = stmt.where(Relation.provenance.in_(provenance))
    rels = list(db.scalars(stmt))
    for r in rels:
        g.add_edge(r.source_entity_id, r.target_entity_id, key=r.id)
    return g, entities, {r.id: r for r in rels}


def explore(
    db: Session, user: User, *, focus: int | None, depth: int, relation_types: list[str] | None,
    provenance: list[str] | None, entity_types: list[str] | None, max_nodes: int = 300,
) -> GraphOut:
    g, entities, rels = _graph(db, user, relation_types, provenance)
    if focus is not None:
        get_entity(db, user, focus)
        und = g.to_undirected(as_view=True)
        keep = set(nx.single_source_shortest_path_length(und, focus, cutoff=depth))
    else:
        keep = set(g.nodes)
    if entity_types:
        keep = {n for n in keep if entities[n].entity_type in entity_types or n == focus}
    if focus is None:
        # Senza focus si mostrano solo entità con almeno un collegamento (più leggibile), fino al limite.
        connected = {n for n in keep if g.degree(n) > 0}
        keep = connected or keep
    keep = set(sorted(keep, key=lambda n: -g.degree(n))[:max_nodes])
    sub = g.subgraph(keep)
    simple = nx.Graph(sub.to_undirected())
    pos = nx.spring_layout(simple, seed=42, k=None) if len(simple) > 1 else {n: (0.0, 0.0) for n in simple}
    btw = nx.betweenness_centrality(simple) if 2 < len(simple) <= 400 else {n: 0.0 for n in simple}
    nodes = [
        GraphNode(id=n, name=entities[n].name, entity_type=entities[n].entity_type, x=float(pos[n][0]), y=float(pos[n][1]),
                  degree=int(sub.degree(n)), betweenness=round(float(btw.get(n, 0.0)), 4), is_focus=n == focus)
        for n in sub.nodes
    ]
    edges = [relation_out(db, rels[k]) for _, _, k in sub.edges(keys=True)]
    stats = {
        "entities": len(entities), "relations": len(rels), "shown_nodes": len(nodes), "shown_edges": len(edges),
        "components": nx.number_connected_components(simple) if len(simple) else 0,
        "by_provenance": {p: sum(1 for e in edges if e.provenance == p) for p in PROVENANCE_LABEL},
    }
    return GraphOut(nodes=nodes, edges=edges, stats=stats)


def path(db: Session, user: User, a: int, b: int) -> PathOut:
    get_entity(db, user, a)
    get_entity(db, user, b)
    g, _, rels = _graph(db, user, None, None)
    und = nx.Graph()
    edge_for: dict[tuple[int, int], int] = {}
    for u, v, k in g.edges(keys=True):
        und.add_edge(u, v)
        edge_for.setdefault((min(u, v), max(u, v)), k)
    try:
        nodes = nx.shortest_path(und, a, b)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return PathOut(found=False, entity_ids=[], relations=[])
    rel_ids = [edge_for[(min(u, v), max(u, v))] for u, v in zip(nodes, nodes[1:])]
    return PathOut(found=True, entity_ids=nodes, relations=[relation_out(db, rels[r]) for r in rel_ids])
