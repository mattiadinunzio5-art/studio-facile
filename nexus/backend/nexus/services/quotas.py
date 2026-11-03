"""Limiti d'uso per piano. Fase 2–7: il piano 'free' locale non ha limiti
stringenti; i valori effettivi sono definiti in core/plans.py (Fase 8)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import User


def check(db: Session, user: User, resource: str, extra_bytes: int = 0) -> None:  # noqa: ARG001
    from ..core import plans

    plans.enforce(db, user, resource, extra_bytes=extra_bytes)
