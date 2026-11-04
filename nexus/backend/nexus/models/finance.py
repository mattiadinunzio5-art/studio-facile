from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, TimestampMixin

SERIES_CATEGORIES = (
    "stocks", "indices", "bonds", "commodities", "precious_metals", "fx", "crypto", "rates",
    "inflation", "public_debt", "gdp", "unemployment", "trade_balance", "other",
)
FREQUENCIES = ("D", "W", "M", "Q", "A")


class Series(TimestampMixin, Base):
    """Serie storica con metadati di provenienza completi."""

    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(20), default="other", nullable=False)
    country: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    connector: Mapped[str] = mapped_column(String(30), nullable=False)  # world-bank | fred | owid | eurostat | upload
    source_series_id: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    source_label: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    license_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    unit: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    frequency: Mapped[str] = mapped_column(String(1), nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_last_updated: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    from_cache: Mapped[bool] = mapped_column(default=False, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)

    observations: Mapped[list["Observation"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="Observation.date"
    )


class Observation(Base):
    """Osservazione. ``date`` è l'inizio del periodo (AAAA-MM-GG); ``value`` None = dato mancante."""

    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("series_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)


class Credential(TimestampMixin, Base):
    """Credenziale per un servizio esterno, cifrata a riposo (Fernet)."""

    __tablename__ = "credentials"
    __table_args__ = (UniqueConstraint("owner_id", "provider"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    secret_encrypted: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hint: Mapped[str] = mapped_column(String(12), default="", nullable=False)  # ultime cifre, per riconoscerla
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # es. base_url, model (non segreti)
