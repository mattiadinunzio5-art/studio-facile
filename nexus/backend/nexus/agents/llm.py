"""Client dei provider AI intercambiabili.

Nessun provider è attivo per impostazione predefinita. Un provider viene usato
solo se l'utente ha configurato le credenziali (Sistema → Credenziali) e lo ha
selezionato. Ogni chiamata restituisce testo, modello, consumo e motivo di
arresto: la piattaforma registra tutto nel run degli agenti.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

ANTHROPIC_DEFAULT_MODEL = "claude-opus-5-5"
# Modelli che accettano il fallback lato server in caso di rifiuto (beta server-side-fallback-2026-07-01).
_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


class ProviderError(Exception):
    """Errore del provider, con messaggio comprensibile e indicazione se ritentabile."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    stop_reason: str | None = None
    duration_ms: int = 0
    notes: list[str] = field(default_factory=list)


class LLMClient:
    provider = "none"
    model = ""

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> LLMResult:  # pragma: no cover - interfaccia
        raise NotImplementedError


class OllamaClient(LLMClient):
    provider = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 300.0, client: httpx.Client | None = None):
        if not model:
            raise ProviderError("Ollama: indica il nome del modello locale (es. quello scaricato con 'ollama pull').")
        self.base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")
        self.model = model
        self.http = client or httpx.Client(timeout=timeout)

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> LLMResult:
        t0 = time.perf_counter()
        try:
            r = self.http.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "stream": False, "format": "json", "options": {"num_predict": max_tokens},
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama non raggiungibile su {self.base_url}: {type(exc).__name__}", retryable=True) from exc
        if r.status_code != 200:
            raise ProviderError(f"Ollama ha risposto HTTP {r.status_code}: {r.text[:200]}", retryable=r.status_code >= 500)
        d = r.json()
        return LLMResult(
            text=d.get("message", {}).get("content", ""), provider=self.provider, model=self.model,
            input_tokens=d.get("prompt_eval_count"), output_tokens=d.get("eval_count"),
            stop_reason=d.get("done_reason"), duration_ms=int((time.perf_counter() - t0) * 1000),
        )


class OpenAICompatibleClient(LLMClient):
    provider = "openai-compatible"

    def __init__(self, base_url: str, api_key: str | None, model: str, timeout: float = 300.0, client: httpx.Client | None = None):
        if not base_url or not model:
            raise ProviderError("Endpoint compatibile OpenAI: servono base_url e model.")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.http = client or httpx.Client(timeout=timeout)

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> LLMResult:
        t0 = time.perf_counter()
        try:
            r = self.http.post(
                f"{self.base_url}/chat/completions", headers=self.headers,
                json={"model": self.model, "max_tokens": max_tokens,
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Endpoint non raggiungibile: {type(exc).__name__}", retryable=True) from exc
        if r.status_code in (401, 403):
            raise ProviderError("Credenziali rifiutate dall'endpoint.")
        if r.status_code == 429:
            raise ProviderError("Limite di richieste raggiunto presso il fornitore.", retryable=True)
        if r.status_code != 200:
            raise ProviderError(f"L'endpoint ha risposto HTTP {r.status_code}: {r.text[:200]}", retryable=r.status_code >= 500)
        d = r.json()
        choice = (d.get("choices") or [{}])[0]
        usage = d.get("usage") or {}
        return LLMResult(
            text=(choice.get("message") or {}).get("content") or "", provider=self.provider, model=d.get("model", self.model),
            input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"),
            stop_reason=choice.get("finish_reason"), duration_ms=int((time.perf_counter() - t0) * 1000),
        )


class AnthropicClient(LLMClient):
    """Anthropic Messages API tramite l'SDK ufficiale. A pagamento: usato solo con chiave dell'utente."""

    provider = "anthropic"

    def __init__(self, api_key: str, model: str | None = None, effort: str = "medium", sdk_client=None):
        import anthropic

        if not api_key and sdk_client is None:
            raise ProviderError("Anthropic: chiave API mancante.")
        self.model = model or ANTHROPIC_DEFAULT_MODEL
        self.effort = effort
        self.client = sdk_client or anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=600.0)

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> LLMResult:
        import anthropic

        t0 = time.perf_counter()
        kwargs = dict(
            model=self.model, max_tokens=max(max_tokens, 16000), system=system,
            messages=[{"role": "user", "content": user}], output_config={"effort": self.effort},
        )
        notes = []
        try:
            if self.model in _FALLBACK_MODELS:
                # In caso di rifiuto dei classificatori di sicurezza la richiesta viene
                # rieseguita lato server sul modello di ripiego raccomandato.
                resp = self.client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
            else:
                resp = self.client.messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise ProviderError("Chiave Anthropic non valida.") from exc
        except anthropic.PermissionDeniedError as exc:
            raise ProviderError("La chiave Anthropic non ha i permessi necessari.") from exc
        except anthropic.NotFoundError as exc:
            raise ProviderError(f"Modello Anthropic inesistente: {self.model}") from exc
        except anthropic.RateLimitError as exc:
            raise ProviderError("Limite di richieste Anthropic raggiunto: riprova più tardi.", retryable=True) from exc
        except anthropic.BadRequestError as exc:
            raise ProviderError(f"Richiesta non valida: {exc.message}") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"Errore Anthropic HTTP {exc.status_code}.", retryable=exc.status_code >= 500) from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError("Anthropic non raggiungibile (rete).", retryable=True) from exc
        if resp.stop_reason == "refusal":
            raise ProviderError("Il modello ha rifiutato la richiesta (stop_reason: refusal).")
        if any(getattr(e, "type", "") == "fallback_message" for e in (getattr(resp.usage, "iterations", None) or [])):
            notes.append("Risposta prodotta dal modello di ripiego dopo un rifiuto.")
        text = "".join(b.text for b in resp.content if b.type == "text")
        return LLMResult(
            text=text, provider=self.provider, model=resp.model, input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens, stop_reason=resp.stop_reason,
            duration_ms=int((time.perf_counter() - t0) * 1000), notes=notes,
        )
