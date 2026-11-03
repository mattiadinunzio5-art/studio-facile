"""Estrazione del testo dai documenti importati.

Ogni estrattore restituisce una lista di ``Section`` con un *locator* che
permette di citare con precisione il punto del documento (pagina, righe,
paragrafo). Nessun contenuto viene interpretato o eseguito.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".csv": "csv",
    ".txt": "txt",
    ".md": "md",
    ".xlsx": "xlsx",
}


class ExtractionError(Exception):
    pass


@dataclass
class Section:
    text: str
    page: int | None = None
    locator: str = ""


@dataclass
class Extracted:
    sections: list[Section]
    page_count: int | None = None
    title: str | None = None
    author: str | None = None


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _CONTROL.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # parole spezzate a fine riga
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_kind(filename: str, head: bytes) -> str:
    ext = Path(filename).suffix.lower()
    kind = EXTENSIONS.get(ext)
    if kind is None:
        raise ExtractionError(f"Formato non supportato: '{ext or 'senza estensione'}'. Ammessi: {', '.join(EXTENSIONS)}")
    # Verifica la firma del file: l'estensione da sola non basta.
    if kind == "pdf" and not head.startswith(b"%PDF"):
        raise ExtractionError("Il file non è un PDF valido.")
    if kind in ("docx", "xlsx") and not head.startswith(b"PK"):
        raise ExtractionError(f"Il file non è un {kind.upper()} valido.")
    if kind in ("csv", "txt", "md") and b"\x00" in head[:4096]:
        raise ExtractionError("Il file di testo contiene dati binari.")
    return kind


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ExtractionError("Codifica del testo non riconosciuta.")


def extract_pdf(data: bytes) -> Extracted:
    import pymupdf

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"PDF non leggibile: {exc}") from exc
    if doc.needs_pass:
        raise ExtractionError("PDF protetto da password.")
    sections = []
    for i, page in enumerate(doc, start=1):
        txt = clean_text(page.get_text("text"))
        if txt:
            sections.append(Section(txt, page=i, locator=f"p. {i}"))
    meta = doc.metadata or {}
    n = doc.page_count
    doc.close()
    if not sections:
        raise ExtractionError(
            "Nessun testo estraibile: il PDF sembra una scansione. L'OCR non è incluso (previsto come estensione)."
        )
    return Extracted(sections, page_count=n, title=meta.get("title") or None, author=meta.get("author") or None)


def extract_docx(data: bytes) -> Extracted:
    import docx

    try:
        d = docx.Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"DOCX non leggibile: {exc}") from exc
    sections: list[Section] = []
    heading = ""
    buf: list[str] = []
    start = 1

    def flush(end: int):
        text = clean_text("\n".join(buf))
        if text:
            loc = f"§ {start}–{end}" + (f" ({heading[:40]})" if heading else "")
            sections.append(Section(text, locator=loc))

    paras = [p for p in d.paragraphs]
    for idx, p in enumerate(paras, start=1):
        style = (p.style.name if p.style is not None else "") or ""
        if style.lower().startswith(("heading", "titolo")) and buf:
            flush(idx - 1)
            buf, start = [], idx
        if style.lower().startswith(("heading", "titolo")):
            heading = p.text.strip()
        if p.text.strip():
            buf.append(p.text)
    flush(len(paras))
    for t_i, table in enumerate(d.tables, start=1):
        rows = [" | ".join(c.text.strip() for c in r.cells) for r in table.rows]
        txt = clean_text("\n".join(rows))
        if txt:
            sections.append(Section(txt, locator=f"tabella {t_i}"))
    props = d.core_properties
    if not sections:
        raise ExtractionError("Il documento DOCX non contiene testo.")
    return Extracted(sections, title=props.title or None, author=props.author or None)


def _table_sections(df, label: str, rows_per_section: int = 40) -> list[Section]:
    sections = []
    cols = [str(c) for c in df.columns]
    for start in range(0, len(df), rows_per_section):
        part = df.iloc[start : start + rows_per_section]
        lines = []
        for _, row in part.iterrows():
            cells = [f"{c}: {v}" for c, v in zip(cols, row.tolist()) if str(v) not in ("", "nan", "None")]
            lines.append("; ".join(cells))
        end = start + len(part)
        sections.append(Section(clean_text("\n".join(lines)), locator=f"{label}righe {start + 1}–{end}"))
    return sections


def extract_csv(data: bytes) -> Extracted:
    import pandas as pd

    text = _decode(data)
    try:
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"CSV non leggibile: {exc}") from exc
    if df.empty:
        raise ExtractionError("Il CSV non contiene righe.")
    header = Section("Colonne: " + ", ".join(map(str, df.columns)), locator="intestazione")
    return Extracted([header, *_table_sections(df, "")])


def extract_xlsx(data: bytes) -> Extracted:
    import pandas as pd

    try:
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, dtype=str, engine="openpyxl")
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"XLSX non leggibile: {exc}") from exc
    sections: list[Section] = []
    for name, df in sheets.items():
        df = df.fillna("")
        if df.empty:
            continue
        sections.append(Section(f"Foglio {name}. Colonne: " + ", ".join(map(str, df.columns)), locator=f"{name}: intestazione"))
        sections.extend(_table_sections(df, f"{name}: "))
    if not sections:
        raise ExtractionError("Il file XLSX non contiene dati.")
    return Extracted(sections)


def extract_text_file(data: bytes) -> Extracted:
    text = clean_text(_decode(data))
    if not text:
        raise ExtractionError("Il file è vuoto.")
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    sections = []
    # Gruppi di paragrafi numerati per poterli citare.
    for i in range(0, len(paras), 8):
        group = paras[i : i + 8]
        sections.append(Section("\n\n".join(group), locator=f"§ {i + 1}–{i + len(group)}"))
    return Extracted(sections)


def extract(kind: str, data: bytes) -> Extracted:
    return {
        "pdf": extract_pdf,
        "docx": extract_docx,
        "csv": extract_csv,
        "xlsx": extract_xlsx,
        "txt": extract_text_file,
        "md": extract_text_file,
    }[kind](data)
