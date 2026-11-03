"""Dipendenze FastAPI condivise."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..database.session import Database
from ..models import User
from ..security.identity import ensure_local_user


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_db(request: Request) -> Iterator[Session]:
    yield from get_database(request).session()


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_current_user(db: Annotated[Session, Depends(get_db)]) -> User:
    # Fase 1: utente locale unico. Sostituito dall'autenticazione in Fase 8.
    return ensure_local_user(db)


DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]
