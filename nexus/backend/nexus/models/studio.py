from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, TimestampMixin

# Struttura obbligatoria del rapporto (il titolo è un campo del rapporto, la bibliografia è generata).
STANDARD_SECTIONS = (
    ("abstract", "Abstract"),
    ("introduction", "Introduzione"),
    ("methodology", "Metodologia"),
    ("analysis", "Analisi"),
    ("evidence", "Evidenze"),
    ("counterarguments", "Controargomentazioni"),
    ("conclusions", "Conclusioni"),
    ("limitations", "Limiti"),
)


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    author: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)  # draft | approved
    # Fonti aggiunte esplicitamente alla bibliografia, oltre a quelle citate nel testo.
    source_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    origin: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)  # manual | research_run:<id>
    contains_ai_text: Mapped[bool] = mapped_column(default=False, nullable=False)

    sections: Mapped[list["ReportSection"]] = relationship(cascade="all, delete-orphan", passive_deletes=True, order_by="ReportSection.ordinal")


class ReportSection(Base):
    __tablename__ = "report_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    key: Mapped[str] = mapped_column(String(40), nullable=False)  # chiave standard oppure "chapter"
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Grafici e tabelle: [{"type": "series", "series_id": 1, "caption": ""}, {"type": "simulation", ...}, {"type": "table", "columns": [...], "rows": [[...]]}]
    embeds: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class Note(TimestampMixin, Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)


class Briefing(TimestampMixin, Base):
    __tablename__ = "briefings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    trigger: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)  # manual | scheduled
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
