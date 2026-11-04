from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base


class ConnectorState(Base):
    """Esito dell'ultimo controllo di raggiungibilità di una fonte esterna.

    Le definizioni statiche dei connettori stanno in ``integrations/registry.py``;
    qui si salva solo lo stato osservato.
    """

    __tablename__ = "connector_states"

    connector_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    last_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
