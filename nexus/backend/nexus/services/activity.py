"""Registro attività: ogni operazione rilevante viene tracciata."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ActivityLog, User


def record(
    db: Session,
    *,
    user: User | None,
    actor: str,
    action: str,
    summary: str,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
) -> ActivityLog:
    entry = ActivityLog(
        user_id=user.id if user else None,
        actor=actor,
        action=action,
        summary=summary,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
    )
    db.add(entry)
    return entry


def list_for_user(db: Session, user: User, limit: int = 50, offset: int = 0) -> list[ActivityLog]:
    stmt = (
        select(ActivityLog)
        .where((ActivityLog.user_id == user.id) | (ActivityLog.user_id.is_(None)))
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))
