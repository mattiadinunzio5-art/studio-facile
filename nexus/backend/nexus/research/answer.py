"""Risposte basate esclusivamente sui passaggi recuperati (modalità locale).

Senza un provider AI NEXUS non genera testo: estrae dai documenti le frasi più
pertinenti e le restituisce *testualmente*, con documento, pagina/locator e
livello di supporto. Ogni affermazione è classificata:

- ``documented_fact``: frase riportata alla lettera da un documento importato.
  Indica che il documento AFFERMA qualcosa, non che sia vero: l'attendibilità
  dipende dalla fonte.
- ``missing``: nessun passaggio pertinente trovato.

Interpretazioni, ipotesi e stime richiedono un modello AI (Fase 5) e sono
sempre etichettate come tali.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chunking import split_sentences
from .text import stem, terms

CLAIM_TYPES = ("documented_fact", "interpretation", "hypothesis", "estimate", "missing")


def coverage(query: str, passage: str) -> float:
    q = {stem(t) for t in terms(query)}
    if not q:
        return 0.0
    p = {stem(t) for t in terms(passage)}
    return len(q & p) / len(q)


def support_level(cov: float) -> str:
    if cov >= 0.75:
        return "strong"
    if cov >= 0.4:
        return "partial"
    if cov > 0:
        return "weak"
    return "none"


@dataclass
class Passage:
    chunk_id: int
    document_id: int
    document_title: str
    page: int | None
    locator: str
    text: str
    score: float
    injection_flag: bool
    source_label: str


def extract_claims(query: str, passages: list[Passage], max_claims: int = 5) -> list[dict]:
    candidates = []
    for p in passages:
        for s in split_sentences(p.text):
            if len(s) < 25:
                continue
            cov = coverage(query, s)
            if cov > 0:
                candidates.append((cov, p.score, s, p))
    candidates.sort(key=lambda x: (-x[0], -x[1]))
    claims, seen = [], set()
    for cov, _, sentence, p in candidates:
        key = sentence.lower()[:120]
        if key in seen:
            continue
        seen.add(key)
        claims.append(
            {
                "type": "documented_fact",
                "text": sentence,
                "support": support_level(cov),
                "coverage": round(cov, 2),
                "evidence": [p.chunk_id],
                "note": "Citazione testuale: indica ciò che il documento afferma, non ne garantisce la veridicità.",
            }
        )
        if len(claims) >= max_claims:
            break
    if not claims:
        claims.append(
            {
                "type": "missing",
                "text": "Nessun passaggio dell'archivio risponde alla domanda.",
                "support": "none",
                "coverage": 0.0,
                "evidence": [],
                "note": "Dato mancante: importa documenti pertinenti o riformula la domanda.",
            }
        )
    return claims
