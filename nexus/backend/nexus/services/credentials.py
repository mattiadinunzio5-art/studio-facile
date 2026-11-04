from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_finance import CredentialIn, CredentialOut
from ..core.config import Settings
from ..core.errors import NotFoundError, ValidationFailedError
from ..models import Credential, User
from ..security import secrets
from . import activity

PROVIDERS = ("fred", "openai-compatible", "anthropic", "ollama")


def _out(provider: str, c: Credential | None) -> CredentialOut:
    return CredentialOut(provider=provider, configured=c is not None, hint=c.hint if c else "",
                         config=c.config if c else {}, updated_at=c.updated_at if c else None)


def list_credentials(db: Session, user: User) -> list[CredentialOut]:
    rows = {c.provider: c for c in db.scalars(select(Credential).where(Credential.owner_id == user.id))}
    return [_out(p, rows.get(p)) for p in PROVIDERS]


def set_credential(db: Session, user: User, settings: Settings, data: CredentialIn) -> CredentialOut:
    if data.provider in ("fred", "anthropic") and not data.secret:
        raise ValidationFailedError("La chiave API è obbligatoria per questo servizio.")
    if data.provider in ("openai-compatible", "ollama") and data.base_url and not data.base_url.startswith(("http://", "https://")):
        raise ValidationFailedError("base_url deve iniziare con http:// o https://")
    if data.provider == "openai-compatible" and not (data.base_url and data.model):
        raise ValidationFailedError("Per un endpoint compatibile OpenAI servono base_url e model.")
    c = db.scalar(select(Credential).where(Credential.owner_id == user.id, Credential.provider == data.provider))
    if c is None:
        c = Credential(owner_id=user.id, provider=data.provider)
        db.add(c)
    c.secret_encrypted = secrets.encrypt(settings, data.secret) if data.secret else ""
    c.hint = secrets.hint(data.secret) if data.secret else ""
    c.config = {k: v for k, v in {"base_url": data.base_url, "model": data.model}.items() if v}
    activity.record(db, user=user, actor="user", action="credential.set", entity_type="credential", entity_id=data.provider,
                    summary=f"Configurata la credenziale per {data.provider}")
    db.commit()
    db.refresh(c)
    return _out(data.provider, c)


def delete_credential(db: Session, user: User, provider: str) -> None:
    c = db.scalar(select(Credential).where(Credential.owner_id == user.id, Credential.provider == provider))
    if c is None:
        raise NotFoundError("Credenziale non configurata.")
    db.delete(c)
    activity.record(db, user=user, actor="user", action="credential.delete", entity_type="credential", entity_id=provider,
                    summary=f"Rimossa la credenziale per {provider}")
    db.commit()


def get_secret(db: Session, user: User, settings: Settings, provider: str) -> tuple[str | None, dict]:
    c = db.scalar(select(Credential).where(Credential.owner_id == user.id, Credential.provider == provider))
    if c is None:
        return None, {}
    return secrets.decrypt(settings, c.secret_encrypted), dict(c.config)
