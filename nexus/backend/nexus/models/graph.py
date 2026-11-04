from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin

ENTITY_TYPES = ("person", "state", "company", "bank", "institution", "event", "document", "theory", "indicator")
RELATION_TYPES = (
    "caused",
    "influenced",
    "contemporary_of",
    "related_to",
    "financed",
    "involved_in",
    "replaced",
    "preceded",
)
# sourced: supportata da una fonte o da un passaggio di documento (obbligatori)
# user_hypothesis: ipotesi dichiarata dall'utente · ai_hypothesis: ipotesi generata da un modello AI
PROVENANCE = ("sourced", "user_hypothesis", "ai_hypothesis")


class Entity(TimestampMixin, Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("owner_id", "event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    aliases: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("historical_events.id", ondelete="CASCADE"), nullable=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)


class Relation(TimestampMixin, Base):
    __tablename__ = "relations"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    source_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False)
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False)
    relation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provenance: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    evidence_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), default="medium", nullable=False)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Run AI che ha generato l'ipotesi (Fase 5), per tracciabilità.
    ai_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
