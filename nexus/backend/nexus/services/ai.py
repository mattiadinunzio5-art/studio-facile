"""Selezione del provider AI per utente e costruzione del client."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..agents import llm
from ..agents.providers import AI_PROVIDERS
from ..core.config import Settings
from ..core.errors import ValidationFailedError
from ..models import User, UserPreference
from . import activity, credentials

PREF_KEY = "ai.provider"


def selected_provider(db: Session, user: User, settings: Settings) -> str:
    pref = db.get(UserPreference, (user.id, PREF_KEY))
    if pref:
        return pref.value.get("provider", "none")
    return settings.ai_provider if settings.ai_provider in {p.id for p in AI_PROVIDERS} else "none"


def select_provider(db: Session, user: User, settings: Settings, provider: str, effort: str = "medium") -> dict:
    if provider not in {p.id for p in AI_PROVIDERS}:
        raise ValidationFailedError("Provider sconosciuto.")
    if provider != "none":
        secret, cfg = credentials.get_secret(db, user, settings, provider)
        if secret is None and not cfg:
            raise ValidationFailedError("Configura prima le credenziali di questo provider (Sistema → Credenziali).")
    value = {"provider": provider, "effort": effort}
    pref = db.get(UserPreference, (user.id, PREF_KEY))
    if pref:
        pref.value = value
    else:
        db.add(UserPreference(user_id=user.id, key=PREF_KEY, value=value))
    activity.record(db, user=user, actor="user", action="ai.provider", summary=f"Provider AI selezionato: {provider}")
    db.commit()
    return value


def client_for(db: Session, user: User, settings: Settings) -> llm.LLMClient | None:
    """Client del provider selezionato, oppure None in modalità locale."""
    provider = selected_provider(db, user, settings)
    if provider == "none":
        return None
    secret, cfg = credentials.get_secret(db, user, settings, provider)
    pref = db.get(UserPreference, (user.id, PREF_KEY))
    effort = (pref.value.get("effort") if pref else None) or "medium"
    if provider == "ollama":
        return llm.OllamaClient(cfg.get("base_url", ""), cfg.get("model", ""))
    if provider == "openai-compatible":
        return llm.OpenAICompatibleClient(cfg.get("base_url", ""), secret, cfg.get("model", ""))
    if provider == "anthropic":
        if not secret:
            raise llm.ProviderError("Chiave Anthropic non configurata.")
        return llm.AnthropicClient(secret, cfg.get("model") or None, effort=effort)
    return None


def effective_provider(db: Session, user: User, settings: Settings) -> str:
    """Provider realmente utilizzabile: 'none' se mancano le credenziali."""
    provider = selected_provider(db, user, settings)
    if provider == "none":
        return "none"
    secret, cfg = credentials.get_secret(db, user, settings, provider)
    if provider in ("anthropic",) and not secret:
        return "none"
    if provider in ("ollama", "openai-compatible") and not cfg:
        return "none"
    return provider
