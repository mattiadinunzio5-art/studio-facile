"""Registro dei provider AI intercambiabili.

Per impostazione predefinita nessun provider è attivo: NEXUS lavora in modalità
locale. I provider esterni vengono usati solo se l'utente configura
volontariamente le credenziali e li seleziona (vedi services/ai.py).
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
        implemented=True,
        notes="Gratuito, gira sul tuo computer: richiede Ollama installato e un modello scaricato.",
    ),
    AIProviderDefinition(
        id="openai-compatible",
        name="API compatibile OpenAI",
        kind="remote",
        requires_credentials=True,
        implemented=True,
        notes="Qualsiasi endpoint /chat/completions configurato dall'utente; costi secondo il fornitore.",
    ),
    AIProviderDefinition(
        id="anthropic",
        name="Anthropic API",
        kind="remote",
        requires_credentials=True,
        implemented=True,
        notes="A pagamento, solo con chiave fornita dall'utente. Modello predefinito claude-opus-5-5.",
    ),
]


def active_provider(configured: str) -> AIProviderDefinition:
    """Restituisce il provider attivo; ricade su 'none' se non implementato."""
    for p in AI_PROVIDERS:
        if p.id == configured and p.implemented:
            return p
    return AI_PROVIDERS[0]
