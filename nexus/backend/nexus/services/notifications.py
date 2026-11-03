from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.errors import NotFoundError
from ..database.base import utcnow
from ..models import Notification, User


def create(db: Session, user: User, title: str, body: str = "", level: str = "info") -> Notification:
    n = Notification(user_id=user.id, title=title, body=body, level=level)
    db.add(n)
    return n


def list_for_user(db: Session, user: User, unread_only: bool = False, limit: int = 50):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    return list(db.scalars(stmt))


def unread_count(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    ) or 0


def mark_read(db: Session, user: User, notification_id: int) -> Notification:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise NotFoundError("Notifica non trovata.")
    if n.read_at is None:
        n.read_at = utcnow()
        db.commit()
    return n


def mark_all_read(db: Session, user: User) -> int:
    items = list_for_user(db, user, unread_only=True, limit=10_000)
    now = utcnow()
    for n in items:
        n.read_at = now
    db.commit()
    return len(items)
