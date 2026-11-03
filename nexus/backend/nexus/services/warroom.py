"""Gestione dei run della Research War Room (supervisionati)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import llm, workflow
from ..api.schemas_agents import DecisionIn, RunCreate
from ..api.schemas_history import RelationIn
from ..core.config import Settings
from ..core.errors import NexusError, NotFoundError, ValidationFailedError
from ..database.base import utcnow
from ..database.session import Database
from ..models import Project, ResearchRun, User
from . import activity, ai, graph, notifications, quotas


class InvalidStateError(NexusError):
    status_code = 409
    code = "invalid_state"


def create_run(db: Session, user: User, settings: Settings, data: RunCreate) -> ResearchRun:
    if data.project_id is not None:
        p = db.get(Project, data.project_id)
        if p is None or p.owner_id != user.id:
            raise ValidationFailedError("Progetto inesistente.")
    try:
        client = ai.client_for(db, user, settings)
    except llm.ProviderError as exc:
        raise ValidationFailedError(str(exc)) from exc
    mode = "ai" if client else "local"
    if mode == "ai":
        quotas.check(db, user, "ai_runs")
    running = db.scalar(select(ResearchRun).where(ResearchRun.owner_id == user.id, ResearchRun.status.in_(("queued", "running"))))
    if running:
        raise InvalidStateError("C'è già una ricerca in corso: attendi che termini (limite alle operazioni automatiche).")
    run = ResearchRun(owner_id=user.id, project_id=data.project_id, question=data.question, mode=mode,
                      provider=client.provider if client else "none", model=client.model if client else "",
                      options={"document_ids": data.document_ids, "series_ids": data.series_ids})
    db.add(run)
    db.flush()
    activity.record(db, user=user, actor="user", action="research.start", entity_type="research_run", entity_id=run.id,
                    summary=f"Avviata ricerca ({'AI: ' + run.provider if mode == 'ai' else 'locale'}): «{data.question[:80]}»")
    db.commit()
    db.refresh(run)
    return run


def execute_in_background(database: Database, settings: Settings, run_id: int) -> None:
    """Eseguito fuori dalla richiesta HTTP, con una sessione propria."""
    with database.session_factory() as db:
        run = db.get(ResearchRun, run_id)
        if run is None:
            return
        user = db.get(User, run.owner_id)
        try:
            client = ai.client_for(db, user, settings) if run.mode == "ai" else None
        except llm.ProviderError as exc:
            run.status, run.error, run.finished_at = "failed", str(exc), utcnow()
            db.commit()
            return
        workflow.execute(db, run, user, settings, client)
        activity.record(db, user=None, actor="ai" if run.mode == "ai" else "system", action="research.finish",
                        entity_type="research_run", entity_id=run.id, summary=f"Ricerca #{run.id} terminata: {run.status}")
        if run.status == "awaiting_approval":
            notifications.create(db, user, f"Ricerca #{run.id} pronta per l'approvazione", run.question[:200])
        else:
            notifications.create(db, user, f"Ricerca #{run.id} non completata", run.error or "", level="error")
        db.commit()


def list_runs(db: Session, user: User, limit: int = 50) -> list[ResearchRun]:
    return list(db.scalars(select(ResearchRun).where(ResearchRun.owner_id == user.id).order_by(ResearchRun.id.desc()).limit(limit)))


def get_run(db: Session, user: User, run_id: int) -> ResearchRun:
    r = db.get(ResearchRun, run_id)
    if r is None or r.owner_id != user.id:
        raise NotFoundError("Ricerca non trovata.")
    return r


def decide(db: Session, user: User, run_id: int, data: DecisionIn) -> ResearchRun:
    run = get_run(db, user, run_id)
    if run.status != "awaiting_approval":
        raise InvalidStateError("Solo una ricerca in attesa di approvazione può essere approvata o respinta.")
    proposals = run.result.get("proposed_relations", [])
    if data.decision == "reject" and data.accepted_relations:
        raise ValidationFailedError("Una ricerca respinta non può salvare relazioni.")
    created = 0
    for idx in data.accepted_relations:
        if not 0 <= idx < len(proposals):
            raise ValidationFailedError(f"Relazione proposta {idx} inesistente.")
        p = proposals[idx]
        rel = RelationIn(source_entity_id=p["source_entity_id"], target_entity_id=p["target_entity_id"], relation_type=p["relation_type"],
                         provenance="user_hypothesis", evidence_note=f"Proposta dalla ricerca #{run.id}: {p.get('rationale', '')}"[:2000])
        try:
            graph.create_relation(db, user, rel, ai_run_id=run.id, provenance_override="ai_hypothesis")
            created += 1
        except NexusError:
            continue  # duplicata o entità rimossa nel frattempo
    run.status = "approved" if data.decision == "approve" else "rejected"
    run.decision_note, run.decided_at = data.note, utcnow()
    activity.record(db, user=user, actor="user", action=f"research.{run.status}", entity_type="research_run", entity_id=run.id,
                    summary=f"Ricerca #{run.id} {'approvata' if run.status == 'approved' else 'respinta'}" + (f"; {created} ipotesi AI salvate nel grafo" if created else ""))
    db.commit()
    db.refresh(run)
    return run
