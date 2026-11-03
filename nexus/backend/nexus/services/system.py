from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import __version__
from ..agents.providers import AI_PROVIDERS
from ..api.schemas import AIProviderOut, SystemStatusOut
from ..core.config import Settings
from ..database.base import utcnow


def database_ok(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - lo stato del DB è un esito, non un errore
        return False


def status(db: Session, settings: Settings, user=None) -> SystemStatusOut:
    from . import ai

    pid = ai.effective_provider(db, user, settings) if user is not None else "none"
    provider = next(p for p in AI_PROVIDERS if p.id == pid)
    return SystemStatusOut(
        version=__version__,
        environment=settings.env,
        database=settings.database_label,
        database_ok=database_ok(db),
        ai_mode="local" if provider.kind == "local" else "remote",
        ai_provider=AIProviderOut(**provider.__dict__),
        ai_providers=[AIProviderOut(**p.__dict__) for p in AI_PROVIDERS],
        server_time=utcnow(),
    )
