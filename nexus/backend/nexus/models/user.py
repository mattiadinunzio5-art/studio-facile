from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    """Utente. In Fase 1 esiste solo l'utente locale (``is_local=True``).

    Ruoli, piani e autenticazione completi arrivano in Fase 8, ma ogni dato è
    già legato a un ``owner_id`` per garantire la separazione tra utenti.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="owner", nullable=False)
    plan: Mapped[str] = mapped_column(String(20), default="free", nullable=False)
    is_local: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
