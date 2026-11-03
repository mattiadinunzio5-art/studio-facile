"""Generatori di file reali per i test di importazione."""

from __future__ import annotations

import io


def make_pdf(pages: list[str]) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def make_docx(paragraphs: list[tuple[str, str]]) -> bytes:
    import docx

    d = docx.Document()
    for style, text in paragraphs:
        if style == "h":
            d.add_heading(text, level=1)
        else:
            d.add_paragraph(text)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def make_xlsx(rows: list[list]) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dati"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def upload(client, filename: str, data: bytes, **form):
    return client.post("/api/documents", files={"file": (filename, data)}, data=form)
