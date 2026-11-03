"""Suddivisione del testo in segmenti per l'indicizzazione.

I segmenti rispettano i confini di frase quando possibile e conservano il
locator della sezione di origine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .extract import Section

_SENT_SPLIT = re.compile(r"(?<=[.!?;:])\s+(?=[A-ZÀ-ÖØ-Þ0-9«\"'(\[])")


@dataclass
class Chunk:
    text: str
    page: int | None
    locator: str


def split_sentences(text: str) -> list[str]:
    parts: list[str] = []
    for para in re.split(r"\n\s*\n|\n", text):
        para = para.strip()
        if para:
            parts.extend(s.strip() for s in _SENT_SPLIT.split(para) if s.strip())
    return parts


def chunk_sections(sections: list[Section], max_chars: int = 1000, overlap_sentences: int = 1) -> list[Chunk]:
    chunks: list[Chunk] = []
    for sec in sections:
        sentences = split_sentences(sec.text)
        buf: list[str] = []
        size = 0
        for s in sentences:
            # Frase più lunga del limite: la si spezza in blocchi fissi.
            while len(s) > max_chars:
                if buf:
                    chunks.append(Chunk(" ".join(buf), sec.page, sec.locator))
                    buf, size = [], 0
                chunks.append(Chunk(s[:max_chars], sec.page, sec.locator))
                s = s[max_chars:]
            if size + len(s) > max_chars and buf:
                chunks.append(Chunk(" ".join(buf), sec.page, sec.locator))
                buf = buf[-overlap_sentences:] if overlap_sentences else []
                size = sum(len(x) + 1 for x in buf)
            buf.append(s)
            size += len(s) + 1
        if buf:
            text = " ".join(buf)
            if not chunks or chunks[-1].text != text:
                chunks.append(Chunk(text, sec.page, sec.locator))
    return [c for c in chunks if c.text.strip()]
