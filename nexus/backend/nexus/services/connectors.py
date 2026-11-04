from __future__ import annotations

from sqlalchemy.orm import Session

from ..api.schemas import ConnectorOut
from ..core.errors import NotFoundError
from ..database.base import utcnow
from ..integrations import health
from ..integrations.registry import CONNECTORS, CONNECTORS_BY_ID, ConnectorDefinition
from ..models import ConnectorState, User
from . import activity

STATUS_IT = {"reachable": "raggiungibile", "degraded": "risponde con errore", "unreachable": "non raggiungibile"}


def _to_out(defn: ConnectorDefinition, state: ConnectorState | None) -> ConnectorOut:
    return ConnectorOut(
        id=defn.id,
        name=defn.name,
        category=defn.category,
        homepage=defn.homepage,
        terms_url=defn.terms_url,
        requires_api_key=defn.requires_api_key,
        implemented=defn.implemented,
        planned_phase=defn.planned_phase,
        notes=defn.notes,
        last_status=state.last_status if state else "unknown",
        last_checked_at=state.last_checked_at if state else None,
        last_http_status=state.last_http_status if state else None,
        last_latency_ms=state.last_latency_ms if state else None,
        last_error=state.last_error if state else None,
    )


def list_connectors(db: Session) -> list[ConnectorOut]:
    states = {s.connector_id: s for s in db.query(ConnectorState).all()}
    return [_to_out(c, states.get(c.id)) for c in CONNECTORS]


def check_connector(db: Session, user: User, connector_id: str, timeout: float) -> ConnectorOut:
    defn = CONNECTORS_BY_ID.get(connector_id)
    if defn is None:
        raise NotFoundError("Connettore non trovato.")
    result = health.probe(defn.check_url, timeout=timeout)
    state = db.get(ConnectorState, connector_id) or ConnectorState(connector_id=connector_id)
    state.last_checked_at = utcnow()
    state.last_status = result.status
    state.last_http_status = result.http_status
    state.last_latency_ms = result.latency_ms
    state.last_error = result.error
    db.add(state)
    activity.record(
        db,
        user=user,
        actor="user",
        action="connector.check",
        entity_type="connector",
        entity_id=connector_id,
        summary=f"Verifica disponibilità {defn.name}: {STATUS_IT.get(result.status, result.status)}",
    )
    db.commit()
    return _to_out(defn, state)
