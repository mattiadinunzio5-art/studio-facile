"""Controllo di raggiungibilità delle fonti esterne.

Non scarica dati: esegue una singola richiesta GET con timeout e registra esito,
codice HTTP e latenza. Gli errori di rete sono esiti validi ("unreachable"),
non eccezioni: l'app deve funzionare anche con le fonti offline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

USER_AGENT = "NEXUS/0.1 (local research platform; availability check)"


@dataclass
class ProbeResult:
    status: str  # reachable | degraded | unreachable
    http_status: int | None
    latency_ms: int | None
    error: str | None


def probe(url: str, timeout: float, client: httpx.Client | None = None) -> ProbeResult:
    own_client = client is None
    client = client or httpx.Client(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    )
    start = time.perf_counter()
    try:
        resp = client.get(url)
        latency = int((time.perf_counter() - start) * 1000)
        if resp.status_code < 400:
            status = "reachable"
        elif resp.status_code < 500:
            # L'host risponde ma rifiuta la richiesta (es. 403 anti-bot, 429 rate limit).
            status = "degraded"
        else:
            status = "unreachable"
        return ProbeResult(status, resp.status_code, latency, None)
    except httpx.HTTPError as exc:
        return ProbeResult("unreachable", None, None, f"{type(exc).__name__}: {exc}"[:500])
    finally:
        if own_client:
            client.close()
