"""Registro dei provider AI intercambiabili.

In Fase 1 nessun provider è implementato né attivo: NEXUS lavora in modalità
locale. I provider esterni saranno attivati (Fase 5) solo se l'utente
configura volontariamente le proprie credenziali.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AIProviderDefinition:
    id: str
    name: str
    kind: str  # local | remote
    requires_credentials: bool
    implemented: bool
    notes: str


AI_PROVIDERS: list[AIProviderDefinition] = [
    AIProviderDefinition(
        id="none",
        name="Nessuno (modalità locale)",
        kind="local",
        requires_credentials=False,
        implemented=True,
        notes="Ricerca, archivio e analisi locali. Nessuna generazione di testo AI.",
    ),
    AIProviderDefinition(
        id="ollama",
        name="Ollama (modelli locali)",
        kind="local",
        requires_credentials=False,
        implemented=False,
        notes="Previsto in Fase 5. Gratuito, richiede l'installazione locale di Ollama.",
    ),
    AIProviderDefinition(
        id="openai-compatible",
        name="API compatibile OpenAI",
        kind="remote",
        requires_credentials=True,
        implemented=False,
        notes="Previsto in Fase 5. Qualsiasi endpoint compatibile, configurato dall'utente.",
    ),
    AIProviderDefinition(
        id="anthropic",
        name="Anthropic API",
        kind="remote",
        requires_credentials=True,
        implemented=False,
        notes="Previsto in Fase 5. A pagamento, solo con chiave fornita dall'utente.",
    ),
]


def active_provider(configured: str) -> AIProviderDefinition:
    """Restituisce il provider attivo; ricade su 'none' se non implementato."""
    for p in AI_PROVIDERS:
        if p.id == configured and p.implemented:
            return p
    return AI_PROVIDERS[0]
