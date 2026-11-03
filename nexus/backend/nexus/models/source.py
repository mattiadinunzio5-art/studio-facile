from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin

SOURCE_TYPES = ("book", "article", "chapter", "web", "dataset", "archive", "document", "other")
# unverified: inserita dall'utente, non controllata
# verified_user: l'utente dichiara di averla controllata sull'originale
# verified_registry: metadati confermati da un registro esterno (es. Crossref per i DOI)
# not_found: il registro esterno non conosce l'identificativo indicato
VERIFICATION_STATES = ("unverified", "verified_user", "verified_registry", "not_found")


class Source(TimestampMixin, Base):
    """Fonte bibliografica. Mai generata automaticamente: la crea l'utente
    (o un import con metadati reali) e il suo stato di verifica è esplicito."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="other", nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publisher: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    container: Mapped[str] = mapped_column(String(300), default="", nullable=False)  # rivista/volume
    pages: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    doi: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    isbn: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    accessed_at: Mapped[str] = mapped_column(String(10), default="", nullable=False)  # AAAA-MM-GG
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified", nullable=False)
    verification_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
