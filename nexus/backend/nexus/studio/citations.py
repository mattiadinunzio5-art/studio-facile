"""Citazioni nel testo dei rapporti.

Sintassi: ``[@12]`` oppure ``[@12, p. 45]`` / ``[@12, pp. 45-47]``, dove 12 è
l'id di una fonte della bibliografia. In esportazione diventano riferimenti
numerati ``[1, p. 45]`` nell'ordine di prima citazione. Una citazione a una
fonte inesistente non viene mai «risolta»: resta segnalata.
"""

from __future__ import annotations

import re

CITE_RX = re.compile(r"\[@(\d+)(?:,\s*([^\]\n]{1,40}))?\]")


def cited_ids(texts: list[str]) -> list[int]:
    seen: list[int] = []
    for t in texts:
        for m in CITE_RX.finditer(t or ""):
            sid = int(m.group(1))
            if sid not in seen:
                seen.append(sid)
    return seen


def render(text: str, numbering: dict[int, int]) -> str:
    def sub(m: re.Match) -> str:
        sid = int(m.group(1))
        loc = m.group(2)
        if sid not in numbering:
            return "[citazione non valida]"
        return f"[{numbering[sid]}{', ' + loc.strip() if loc else ''}]"

    return CITE_RX.sub(sub, text or "")
