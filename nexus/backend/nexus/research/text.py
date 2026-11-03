"""Utilità linguistiche minime (italiano + inglese) senza dipendenze esterne."""

from __future__ import annotations

import re
import unicodedata

STOPWORDS = set(
    """
a ad al alla alle allo agli ai anche che chi ci come con contro cui da dal dalla dalle dagli dai del della delle dello degli dei di
dove e ed è era erano essere fa fra gli ha hanno ho i il in la le lo l loro ma mi ne nei nel nella nelle nello negli noi non o per perché
più quale quali quando quanto quella quelle quello questi questo questa queste si sia siamo sono su sua sue suo suoi sul sulla tra tu
un una uno vi voi qual cosa cos quali stato stata stati
the of and to in is was were be been are for on with as by at from that this these those it its an or not which who what when where
why how did does do has have had about into than then there their they them
""".split()
)

_WORD = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def terms(text: str) -> list[str]:
    """Termini di contenuto normalizzati (minuscolo, senza accenti, senza stopword)."""
    out = []
    for w in _WORD.findall(text.lower()):
        w = strip_accents(w)
        if len(w) > 1 and w not in STOPWORDS:
            out.append(w)
    return out


def stem(w: str) -> str:
    """Stemming leggero: riduce plurali/flessioni comuni per il confronto dei termini."""
    for suf in ("zioni", "zione", "mente", "ing", "es", "i", "e", "a", "o", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w
