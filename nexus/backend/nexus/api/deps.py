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


def request_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    from ..services.auth import COOKIE_NAME

    return request.cookies.get(COOKIE_NAME)


def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    settings: Settings = request.app.state.settings
    if settings.auth_mode == "local":
        return ensure_local_user(db)
    from ..services import auth

    user, session = auth.user_from_token(db, request_token(request))
    request.state.session_id = session.id
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    from ..services.auth import ForbiddenError

    if user.role not in ("admin", "owner"):
        raise ForbiddenError("Riservato agli amministratori.")
    return user


DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]
