"""Fonti bibliografiche: validazione formale, verifica opzionale, formattazione.

Regola: NEXUS non inventa riferimenti. I metadati provengono dall'utente o da
un registro esterno interrogato su richiesta (Crossref per i DOI). Una fonte
resta "non verificata" finché l'utente o il registro non la confermano.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

DOI_RX = re.compile(r"^10\.\d{4,9}/\S+$")


def normalize_doi(doi: str) -> str:
    doi = doi.strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi, flags=re.I)
    return doi


def valid_doi(doi: str) -> bool:
    return bool(DOI_RX.match(normalize_doi(doi)))


def valid_isbn(isbn: str) -> bool:
    digits = re.sub(r"[\s-]", "", isbn).upper()
    if len(digits) == 10 and re.fullmatch(r"\d{9}[\dX]", digits):
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(digits))
        return total % 11 == 0
    if len(digits) == 13 and digits.isdigit():
        total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(digits))
        return total % 10 == 0
    return False


def valid_url(url: str) -> bool:
    return bool(re.match(r"^https?://[^\s/$.?#].[^\s]*$", url.strip(), re.I))


@dataclass
class RegistryResult:
    status: str  # verified_registry | not_found | unavailable
    note: str
    metadata: dict


def crossref_lookup(doi: str, timeout: float = 8.0, client: httpx.Client | None = None) -> RegistryResult:
    own = client is None
    client = client or httpx.Client(timeout=timeout, headers={"User-Agent": "NEXUS/0.1 (research platform)"})
    try:
        r = client.get(f"https://api.crossref.org/works/{normalize_doi(doi)}")
        if r.status_code == 404:
            return RegistryResult("not_found", "Crossref non conosce questo DOI.", {})
        if r.status_code != 200:
            return RegistryResult("unavailable", f"Crossref ha risposto HTTP {r.status_code}.", {})
        msg = r.json().get("message", {})
        authors = [
            " ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name", "") for a in msg.get("author", [])
        ]
        year = None
        for key in ("published-print", "published-online", "issued"):
            parts = (msg.get(key) or {}).get("date-parts") or []
            if parts and parts[0] and parts[0][0]:
                year = int(parts[0][0])
                break
        meta = {
            "title": (msg.get("title") or [""])[0],
            "authors": [a for a in authors if a],
            "year": year,
            "container": (msg.get("container-title") or [""])[0],
            "publisher": msg.get("publisher", ""),
            "pages": msg.get("page", ""),
        }
        return RegistryResult("verified_registry", "Metadati confermati da Crossref.", meta)
    except httpx.HTTPError as exc:
        return RegistryResult("unavailable", f"Crossref non raggiungibile: {type(exc).__name__}", {})
    finally:
        if own:
            client.close()


def format_citation(src) -> str:
    """Formato autore-data (ispirato a Chicago/APA), costruito solo dai campi presenti."""
    authors = list(src.authors or [])
    if len(authors) > 3:
        a = f"{authors[0]} et al."
    else:
        a = ", ".join(authors)
    parts = []
    parts.append(a or "[Autore non indicato]")
    parts.append(f"({src.year})" if src.year else "(s.d.)")
    title = src.title
    if src.source_type in ("article", "chapter") and src.container:
        parts.append(f"«{title}». {src.container}")
    else:
        parts.append(f"{title}")
    if src.publisher:
        parts.append(src.publisher)
    if src.pages:
        parts.append(f"pp. {src.pages}")
    if src.doi:
        parts.append(f"https://doi.org/{normalize_doi(src.doi)}")
    elif src.url:
        parts.append(src.url + (f" (consultato il {src.accessed_at})" if src.accessed_at else ""))
    text = ". ".join(p.rstrip(".") for p in parts if p) + "."
    return text


VERIFICATION_LABEL = {
    "unverified": "Fonte non verificata",
    "verified_user": "Verificata dall'utente",
    "verified_registry": "Verificata su registro esterno",
    "not_found": "Identificativo non trovato nel registro",
}
