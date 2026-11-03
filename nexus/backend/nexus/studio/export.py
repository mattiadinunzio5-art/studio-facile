"""Esportazione dei rapporti in PDF (ReportLab) e DOCX (python-docx).

L'input è una vista già risolta del rapporto (``ReportView``): sezioni con
testo in cui le citazioni sono già numerate, figure PNG, tabelle e bibliografia
con stato di verifica di ogni fonte.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field


@dataclass
class Figure:
    caption: str
    png: bytes | None = None
    note: str = ""


@dataclass
class Table:
    caption: str
    columns: list[str]
    rows: list[list[str]]


@dataclass
class SectionView:
    title: str
    paragraphs: list[str]
    figures: list[Figure] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)


@dataclass
class BibEntry:
    number: int
    citation: str
    verified: bool
    status_label: str


@dataclass
class ReportView:
    title: str
    subtitle: str
    author: str
    status: str
    generated_at: str
    sections: list[SectionView]
    bibliography: list[BibEntry]
    notices: list[str]


def paragraphs(body: str) -> list[str]:
    return [p.strip() for p in (body or "").replace("\r\n", "\n").split("\n\n") if p.strip()]


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_pdf(v: ReportView) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer
    from reportlab.platypus import Table as RLTable
    from reportlab.platypus import TableStyle

    from .charts import font_bold_path, font_path

    if "NexusSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("NexusSans", font_path()))
        pdfmetrics.registerFont(TTFont("NexusSans-Bold", font_bold_path()))
    base = ParagraphStyle("b", fontName="NexusSans", fontSize=10, leading=14.5, alignment=TA_LEFT, spaceAfter=6)
    h1 = ParagraphStyle("h1", parent=base, fontName="NexusSans-Bold", fontSize=20, leading=24, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base, fontName="NexusSans-Bold", fontSize=13, leading=17, spaceBefore=12, spaceAfter=6)
    small = ParagraphStyle("s", parent=base, fontSize=8, leading=11, textColor=colors.HexColor("#555555"))
    warn = ParagraphStyle("w", parent=small, textColor=colors.HexColor("#9a5b00"))

    story = [Paragraph(_esc(v.title), h1)]
    if v.subtitle:
        story.append(Paragraph(_esc(v.subtitle), base))
    story.append(Paragraph(_esc(f"{v.author + ' · ' if v.author else ''}Generato da NEXUS il {v.generated_at} · Stato: {v.status}"), small))
    for n in v.notices:
        story.append(Paragraph(_esc(n), warn))
    story.append(Spacer(1, 0.4 * cm))
    for s in v.sections:
        story.append(Paragraph(_esc(s.title), h2))
        if not s.paragraphs and not s.figures and not s.tables:
            story.append(Paragraph("[Sezione non compilata]", warn))
        for p in s.paragraphs:
            lines = p.split("\n")
            if all(line.lstrip().startswith(("- ", "• ")) for line in lines):
                story.append(ListFlowable([ListItem(Paragraph(_esc(line.lstrip()[2:]), base)) for line in lines], bulletType="bullet", start="•"))
            else:
                story.append(Paragraph(_esc(p).replace("\n", "<br/>"), base))
        for f in s.figures:
            if f.png:
                img = Image(io.BytesIO(f.png), width=16 * cm, height=7.55 * cm)
                story.append(img)
            story.append(Paragraph(_esc(f.caption + (f" — {f.note}" if f.note else "")), small))
        for t in s.tables:
            data = [[Paragraph(_esc(c), small) for c in t.columns]] + [[Paragraph(_esc(str(c)), small) for c in r] for r in t.rows]
            tbl = RLTable(data, repeatRows=1, hAlign="LEFT")
            tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                                     ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story += [tbl, Paragraph(_esc(t.caption), small)]
    story.append(Paragraph("Bibliografia", h2))
    if not v.bibliography:
        story.append(Paragraph("Nessuna fonte citata.", warn))
    for b in v.bibliography:
        mark = "" if b.verified else f" [{b.status_label}]"
        story.append(Paragraph(_esc(f"[{b.number}] {b.citation}{mark}"), base))

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("NexusSans", 7)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(2 * cm, 1.2 * cm, f"NEXUS · {v.title[:80]}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Pagina {doc.page}")
        if v.status != "Approvato":
            canvas.setFont("NexusSans-Bold", 54)
            canvas.setFillColor(colors.Color(0.8, 0.8, 0.8, alpha=0.25))
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(40)
            canvas.drawCentredString(0, 0, "BOZZA")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                            title=v.title, author=v.author or "NEXUS")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def to_docx(v: ReportView) -> bytes:
    import docx
    from docx.shared import Cm, Pt, RGBColor

    d = docx.Document()
    d.core_properties.title = v.title
    d.core_properties.author = v.author or "NEXUS"
    d.add_heading(v.title, level=0)
    if v.subtitle:
        d.add_paragraph(v.subtitle)
    meta = d.add_paragraph(f"{v.author + ' · ' if v.author else ''}Generato da NEXUS il {v.generated_at} · Stato: {v.status}")
    meta.runs[0].font.size = Pt(8)
    for n in v.notices:
        r = d.add_paragraph().add_run(n)
        r.font.size, r.font.color.rgb = Pt(8), RGBColor(0x9A, 0x5B, 0x00)
    for s in v.sections:
        d.add_heading(s.title, level=1)
        if not s.paragraphs and not s.figures and not s.tables:
            d.add_paragraph("[Sezione non compilata]")
        for p in s.paragraphs:
            lines = p.split("\n")
            if all(line.lstrip().startswith(("- ", "• ")) for line in lines):
                for line in lines:
                    d.add_paragraph(line.lstrip()[2:], style="List Bullet")
            else:
                d.add_paragraph(p)
        for f in s.figures:
            if f.png:
                d.add_picture(io.BytesIO(f.png), width=Cm(16))
            cap = d.add_paragraph(f.caption + (f" — {f.note}" if f.note else ""))
            cap.runs[0].font.size = Pt(8)
        for t in s.tables:
            tbl = d.add_table(rows=1, cols=len(t.columns))
            tbl.style = "Table Grid"
            for i, c in enumerate(t.columns):
                tbl.rows[0].cells[i].text = c
            for row in t.rows:
                cells = tbl.add_row().cells
                for i, c in enumerate(row[: len(t.columns)]):
                    cells[i].text = str(c)
            d.add_paragraph(t.caption).runs[0].font.size = Pt(8)
    d.add_heading("Bibliografia", level=1)
    if not v.bibliography:
        d.add_paragraph("Nessuna fonte citata.")
    for b in v.bibliography:
        d.add_paragraph(f"[{b.number}] {b.citation}" + ("" if b.verified else f" [{b.status_label}]"))
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
