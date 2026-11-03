from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, utcnow


class ActivityLog(Base):
    """Registro delle attività (utente e sistema). Solo append."""

    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    actor: Mapped[str] = mapped_column(String(20), nullable=False)  # user | system | ai
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )
