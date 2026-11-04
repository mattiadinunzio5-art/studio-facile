from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, TimestampMixin

EVENT_CATEGORIES = (
    "economic",
    "monetary",
    "banking",
    "industrial",
    "war_geopolitics",
    "revolution",
    "financial_crisis",
    "empires",
    "capitalism",
)
# established: consenso storiografico documentato · probable: ben supportato ma con incertezze
# disputed: interpretazioni in conflitto · unverified: non ancora verificato
RELIABILITY = ("established", "probable", "disputed", "unverified")
KNOWLEDGE_KINDS = ("contemporary", "later_discovery", "archival_release", "historiography")


class HistoricalEvent(TimestampMixin, Base):
    """Evento storico. Le date sono intere (anno negativo = a.C.) per gestire
    anche l'antichità; mese e giorno sono facoltativi (precisione variabile)."""

    __tablename__ = "historical_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    start_year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    start_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    region: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    countries: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    causes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    consequences: Mapped[str] = mapped_column(Text, default="", nullable=False)
    people: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    institutions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    economic_implications: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reliability: Mapped[str] = mapped_column(String(20), default="unverified", nullable=False)
    reliability_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)

    source_links: Mapped[list["EventSource"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    knowledge: Mapped[list["KnowledgeItem"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="KnowledgeItem.known_since_year"
    )


class EventSource(Base):
    __tablename__ = "event_sources"
    __table_args__ = (UniqueConstraint("event_id", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("historical_events.id", ondelete="CASCADE"), index=True, nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False)
    pages: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)


class KnowledgeItem(TimestampMixin, Base):
    """Informazione su un evento con l'anno da cui è nota.

    È la base del filtro anti-senno-di-poi della Time Machine: in una data
    selezionata si mostrano solo le informazioni con ``known_since_year`` <= data.
    """

    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("historical_events.id", ondelete="CASCADE"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    known_since_year: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="contemporary", nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
