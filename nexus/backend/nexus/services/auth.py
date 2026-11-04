"""Account, accesso e sessioni (modalità multi-utente)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.errors import NexusError, ValidationFailedError
from ..database.base import utcnow
from ..models import AuthSession, User
from ..security.passwords import hash_password, password_problems, verify_password
from ..security.ratelimit import LoginLimiter
from . import activity

COOKIE_NAME = "nexus_session"
limiter = LoginLimiter()


class AuthError(NexusError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(NexusError):
    status_code = 403
    code = "forbidden"


class TooManyAttempts(NexusError):
    status_code = 429
    code = "too_many_attempts"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _norm(email: str) -> str:
    return email.strip().lower()


def register(db: Session, settings: Settings, email: str, password: str, display_name: str) -> User:
    if settings.auth_mode != "multi":
        raise ForbiddenError("La registrazione è disponibile solo in modalità multi-utente (NEXUS_AUTH_MODE=multi).")
    if not settings.allow_registration:
        raise ForbiddenError("Le registrazioni sono chiuse: chiedi un invito a un amministratore.")
    email = _norm(email)
    problems = password_problems(password, email)
    if problems:
        raise ValidationFailedError("Password troppo debole: " + "; ".join(problems) + ".")
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise ValidationFailedError("Esiste già un account con questa email.")
    # Il primo account registrato diventa amministratore.
    has_accounts = db.scalar(select(func.count()).select_from(User).where(User.is_local.is_(False))) or 0
    u = User(email=email, display_name=display_name.strip() or email.split("@")[0], role="user" if has_accounts else "admin",
             plan="free", is_local=False, password_hash=hash_password(password))
    db.add(u)
    db.flush()
    activity.record(db, user=u, actor="user", action="auth.register", entity_type="user", entity_id=u.id, summary=f"Nuovo account {email} ({u.role})")
    db.commit()
    db.refresh(u)
    return u


def login(db: Session, settings: Settings, email: str, password: str, user_agent: str, ip: str) -> tuple[User, str]:
    if settings.auth_mode != "multi":
        raise ForbiddenError("In modalità locale non serve l'accesso.")
    email = _norm(email)
    key = f"{email}|{ip}"
    if limiter.blocked(key):
        raise TooManyAttempts("Troppi tentativi falliti: riprova tra 15 minuti.")
    u = db.scalar(select(User).where(func.lower(User.email) == email))
    if u is None or not verify_password(password, u.password_hash):
        limiter.fail(key)
        raise AuthError("Email o password non corretti.")
    if not u.is_active:
        raise AuthError("Account disattivato.")
    limiter.reset(key)
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(user_id=u.id, token_hash=_hash(token), expires_at=utcnow() + timedelta(hours=settings.session_hours),
                       user_agent=user_agent[:300], ip=ip[:64]))
    u.last_login_at = utcnow()
    activity.record(db, user=u, actor="user", action="auth.login", entity_type="user", entity_id=u.id, summary="Accesso effettuato")
    db.commit()
    return u, token


def user_from_token(db: Session, token: str | None) -> tuple[User, AuthSession]:
    if not token:
        raise AuthError("Accesso richiesto.")
    s = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash(token)))
    now = utcnow()
    if s is None:
        raise AuthError("Sessione non valida.")
    expires = s.expires_at if s.expires_at.tzinfo else s.expires_at.replace(tzinfo=now.tzinfo)
    if expires < now:
        db.delete(s)
        db.commit()
        raise AuthError("Sessione scaduta: accedi di nuovo.")
    u = db.get(User, s.user_id)
    if u is None or not u.is_active:
        raise AuthError("Account non attivo.")
    s.last_seen_at = now
    db.commit()
    return u, s


def logout(db: Session, token: str | None) -> None:
    if token:
        s = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash(token)))
        if s:
            db.delete(s)
            db.commit()


def list_sessions(db: Session, user: User) -> list[AuthSession]:
    return list(db.scalars(select(AuthSession).where(AuthSession.user_id == user.id).order_by(AuthSession.id.desc())))


def revoke_session(db: Session, user: User, session_id: int) -> None:
    s = db.get(AuthSession, session_id)
    if s is None or s.user_id != user.id:
        from ..core.errors import NotFoundError

        raise NotFoundError("Sessione non trovata.")
    db.delete(s)
    db.commit()


def change_password(db: Session, user: User, current: str, new: str, keep_session_id: int | None) -> None:
    if user.is_local:
        raise ForbiddenError("L'utente locale non usa password.")
    if not verify_password(current, user.password_hash):
        raise AuthError("Password attuale non corretta.")
    problems = password_problems(new, user.email)
    if problems:
        raise ValidationFailedError("Password troppo debole: " + "; ".join(problems) + ".")
    user.password_hash = hash_password(new)
    # Le altre sessioni vengono chiuse.
    for s in list_sessions(db, user):
        if s.id != keep_session_id:
            db.delete(s)
    activity.record(db, user=user, actor="user", action="auth.password", entity_type="user", entity_id=user.id, summary="Password modificata")
    db.commit()
