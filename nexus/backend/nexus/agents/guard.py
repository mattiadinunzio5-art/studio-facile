"""Controlli sulle risposte dei modelli AI.

Regola cardine: l'AI non può trasformare un'ipotesi in un fatto.
- Un'affermazione «documented_fact» deve citare almeno un'evidenza esistente,
  e il suo testo deve avere sovrapposizione sufficiente con le evidenze citate;
  altrimenti viene declassata (a «interpretation» o «hypothesis»), con nota.
- Gli id di evidenza inesistenti vengono rimossi e segnalati.
- Tipi sconosciuti diventano «hypothesis».
"""

from __future__ import annotations

import json
import re

from ..research.answer import coverage

VALID_TYPES = {"documented_fact", "interpretation", "hypothesis", "estimate", "missing"}
MIN_FACT_COVERAGE = 0.35


class ParseError(ValueError):
    pass


def parse_json(text: str) -> dict:
    """Estrae il primo oggetto JSON dalla risposta (tollerando testo o recinti ``` attorno)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    if start < 0:
        raise ParseError("La risposta del modello non contiene JSON.")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(text[start : i + 1])
                except json.JSONDecodeError as exc:
                    raise ParseError(f"JSON non valido: {exc}") from exc
                if not isinstance(obj, dict):
                    raise ParseError("Il JSON non è un oggetto.")
                return obj
    raise ParseError("JSON incompleto nella risposta del modello.")


def _support(cov: float) -> str:
    return "strong" if cov >= 0.75 else "partial" if cov >= 0.4 else "weak" if cov > 0 else "none"


def validate_claims(raw: object, evidence: dict[str, dict]) -> tuple[list[dict], list[str]]:
    issues: list[str] = []
    if not isinstance(raw, list):
        return [], ["Il modello non ha restituito un elenco di affermazioni."]
    out = []
    for i, c in enumerate(raw[:30], start=1):
        if not isinstance(c, dict) or not str(c.get("text", "")).strip():
            issues.append(f"Affermazione {i} scartata: formato non valido.")
            continue
        text = str(c["text"]).strip()[:2000]
        ctype = c.get("type") if c.get("type") in VALID_TYPES else "hypothesis"
        if c.get("type") not in VALID_TYPES:
            issues.append(f"Affermazione {i}: tipo '{c.get('type')}' sconosciuto, trattata come ipotesi.")
        cited = [str(e) for e in (c.get("evidence") or []) if isinstance(e, (str, int))]
        valid = [e for e in cited if e in evidence]
        if len(valid) < len(cited):
            issues.append(f"Affermazione {i}: rimossi riferimenti inesistenti {sorted(set(cited) - set(valid))}.")
        note = str(c.get("note", ""))[:500]
        cov = max((coverage(text, evidence[e]["text"]) for e in valid), default=0.0)
        if ctype == "documented_fact":
            if not valid:
                ctype = "hypothesis"
                note = "Declassata: presentata come fatto ma senza evidenze valide. " + note
                issues.append(f"Affermazione {i}: 'fatto' senza evidenze → ipotesi.")
            elif cov < MIN_FACT_COVERAGE:
                ctype = "interpretation"
                note = "Declassata: il testo non corrisponde abbastanza alle evidenze citate. " + note
                issues.append(f"Affermazione {i}: 'fatto' poco aderente alle evidenze → interpretazione.")
        if ctype == "missing":
            valid = []
        out.append({"type": ctype, "text": text, "evidence": valid, "support": _support(cov) if valid else "none",
                    "coverage": round(cov, 2), "note": note.strip()})
    return out, issues
