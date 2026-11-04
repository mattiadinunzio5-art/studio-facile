"""Identità dell'utente corrente.

- Modalità ``local`` (predefinita): utente unico, backend su 127.0.0.1.
- Modalità ``multi``: sessione obbligatoria (cookie HttpOnly o token Bearer),
  vedi ``services/auth.py``.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User

LOCAL_USER_EMAIL = "local@nexus.localhost"


def ensure_local_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == LOCAL_USER_EMAIL))
    if user is None:
        user = User(
            email=LOCAL_USER_EMAIL,
            display_name="Utente locale",
            role="owner",
            plan="local",
            is_local=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
