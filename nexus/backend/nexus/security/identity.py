"""Identità dell'utente corrente.

Fase 1: modalità locale a utente unico. Il backend ascolta solo su 127.0.0.1 e
ogni richiesta è attribuita all'utente locale. Tutti i servizi ricevono però
l'utente come parametro e filtrano per ``owner_id``: in Fase 8 basterà
sostituire questa dipendenza con l'autenticazione reale.
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
            plan="free",
            is_local=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
