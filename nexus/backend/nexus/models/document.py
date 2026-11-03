from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, TimestampMixin

DOCUMENT_KINDS = ("pdf", "docx", "csv", "txt", "md", "xlsx")
DOCUMENT_CATEGORIES = ("source_material", "user_work", "dataset")


class Document(TimestampMixin, Base):
    """Documento importato. Il contenuto è sempre trattato come dato, mai come istruzione."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(20), default="source_material", nullable=False)
    origin: Mapped[str] = mapped_column(String(40), default="upload", nullable=False)
    origin_url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    license_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    author: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="indexed", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    flagged_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True, order_by="DocumentChunk.ordinal"
    )


class DocumentChunk(Base):
    """Segmento di testo indicizzato. ``locator`` indica pagina/righe/paragrafo."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locator: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Segnalazione di testo che somiglia a istruzioni per un'AI (possibile prompt injection).
    injection_flag: Mapped[bool] = mapped_column(default=False, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")
