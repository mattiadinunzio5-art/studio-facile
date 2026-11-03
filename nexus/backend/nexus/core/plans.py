"""Piani e limiti d'uso (completati in Fase 8)."""

from __future__ import annotations

from sqlalchemy.orm import Session


def enforce(db: Session, user, resource: str, extra_bytes: int = 0) -> None:  # noqa: ARG001
    return None
