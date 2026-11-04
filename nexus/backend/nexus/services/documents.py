"""Importazione, indicizzazione e gestione dei documenti."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_research import DocumentUpdate
from ..core.config import Settings
from ..core.errors import ConfirmationRequiredError, NexusError, NotFoundError, ValidationFailedError
from ..core.logging import logger
from ..models import Document, DocumentChunk, Project, Source, User
from ..research import index
from ..research.chunking import chunk_sections
from ..research.extract import ExtractionError, detect_kind, extract
from ..research.safety import looks_like_injection
from . import activity, quotas


class DuplicateDocumentError(NexusError):
    status_code = 409
    code = "duplicate_document"


def _check_refs(db: Session, user: User, project_id: int | None, source_id: int | None) -> None:
    if project_id is not None:
        p = db.get(Project, project_id)
        if p is None or p.owner_id != user.id:
            raise ValidationFailedError("Progetto inesistente.")
    if source_id is not None:
        s = db.get(Source, source_id)
        if s is None or s.owner_id != user.id:
            raise ValidationFailedError("Fonte inesistente.")


def import_bytes(
    db: Session,
    user: User,
    settings: Settings,
    *,
    filename: str,
    data: bytes,
    title: str | None = None,
    category: str = "source_material",
    project_id: int | None = None,
    origin: str = "upload",
    origin_url: str = "",
    license_note: str = "",
    author: str = "",
    is_demo: bool = False,
) -> Document:
    if not data:
        raise ValidationFailedError("Il file è vuoto.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ValidationFailedError(f"File troppo grande (massimo {settings.max_upload_mb} MB).")
    quotas.check(db, user, "documents", extra_bytes=len(data))
    _check_refs(db, user, project_id, None)
    filename = Path(filename).name[:300] or "documento"
    try:
        kind = detect_kind(filename, data[:8192])
    except ExtractionError as exc:
        raise ValidationFailedError(str(exc)) from exc

    sha = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.owner_id == user.id, Document.sha256 == sha))
    if existing:
        raise DuplicateDocumentError("Documento già presente nell'archivio.", details={"document_id": existing.id})

    try:
        extracted = extract(kind, data)
    except ExtractionError as exc:
        raise ValidationFailedError(str(exc)) from exc

    user_dir = settings.uploads_dir / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{sha}.{kind}"
    path.write_bytes(data)

    chunks = chunk_sections(extracted.sections)
    doc = Document(
        owner_id=user.id,
        project_id=project_id,
        title=(title or extracted.title or Path(filename).stem)[:300],
        filename=filename,
        kind=kind,
        category=category,
        origin=origin,
        origin_url=origin_url,
        license_note=license_note,
        author=(author or extracted.author or "")[:300],
        sha256=sha,
        size_bytes=len(data),
        storage_path=str(path.relative_to(settings.data_dir)),
        page_count=extracted.page_count,
        char_count=sum(len(s.text) for s in extracted.sections),
        chunk_count=len(chunks),
        is_demo=is_demo,
    )
    db.add(doc)
    db.flush()
    rows = []
    for i, c in enumerate(chunks):
        flag = looks_like_injection(c.text)
        rows.append(
            DocumentChunk(document_id=doc.id, owner_id=user.id, ordinal=i, page=c.page, locator=c.locator, text=c.text, injection_flag=flag)
        )
    db.add_all(rows)
    db.flush()
    doc.flagged_chunks = sum(1 for r in rows if r.injection_flag)
    _embed_neural(settings, rows)
    index.fts_add(db, rows)
    activity.record(
        db, user=user, actor="user", action="document.import", entity_type="document", entity_id=doc.id,
        summary=f"Importato «{doc.title}» ({kind.upper()}, {len(rows)} segmenti"
        + (f", {doc.flagged_chunks} segnalati come possibili istruzioni" if doc.flagged_chunks else "") + ")",
    )
    db.commit()
    index.semantic_index.invalidate(user.id)
    db.refresh(doc)
    return doc


def _embed_neural(settings: Settings, rows: list[DocumentChunk]) -> None:
    if settings.embeddings != "sentence-transformers" or not rows:
        return
    try:
        emb = index.NeuralEmbedder(settings.embedding_model)
        vecs = emb.encode([r.text for r in rows])
        for r, v in zip(rows, vecs):
            r.embedding = np.asarray(v, dtype=np.float32).tobytes()
            r.embedding_model = emb.name
    except Exception as exc:  # noqa: BLE001
        # Gli embedding neurali sono facoltativi: si ripiega su LSA, segnalandolo nel log.
        logger.warning("Embedding neurali non disponibili, uso LSA: %s", exc)


GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
GUTENBERG_LICENSE = (
    "Project Gutenberg: opera in pubblico dominio negli Stati Uniti secondo il catalogo. "
    "Verificare lo status nel proprio paese. Il marchio 'Project Gutenberg' ha condizioni d'uso proprie."
)


def import_gutenberg(db: Session, user: User, settings: Settings, ebook_id: int, title: str, author: str, project_id: int | None) -> Document:
    """Scarica UN testo richiesto dall'utente (nessuna raccolta automatica massiva)."""
    url = GUTENBERG_URL.format(id=ebook_id)
    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "NEXUS/0.1 (single user-requested download)"}) as c:
            r = c.get(url)
    except httpx.HTTPError as exc:
        raise ValidationFailedError(f"Project Gutenberg non raggiungibile: {type(exc).__name__}") from exc
    if r.status_code != 200:
        raise ValidationFailedError(f"Testo non disponibile (HTTP {r.status_code}). Verifica l'ID dell'ebook.")
    return import_bytes(
        db, user, settings, filename=f"gutenberg-{ebook_id}.txt", data=r.content, title=title, author=author,
        project_id=project_id, origin="gutenberg", origin_url=f"https://www.gutenberg.org/ebooks/{ebook_id}",
        license_note=GUTENBERG_LICENSE,
    )


def list_documents(db: Session, user: User, project_id: int | None = None, category: str | None = None) -> list[Document]:
    stmt = select(Document).where(Document.owner_id == user.id)
    if project_id is not None:
        stmt = stmt.where(Document.project_id == project_id)
    if category:
        stmt = stmt.where(Document.category == category)
    return list(db.scalars(stmt.order_by(Document.created_at.desc())))


def get_document(db: Session, user: User, document_id: int) -> Document:
    d = db.get(Document, document_id)
    if d is None or d.owner_id != user.id:
        raise NotFoundError("Documento non trovato.")
    return d


def get_chunks(db: Session, user: User, document_id: int, offset: int = 0, limit: int = 50) -> list[DocumentChunk]:
    get_document(db, user, document_id)
    return list(
        db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.ordinal).offset(offset).limit(limit)
        )
    )


def update_document(db: Session, user: User, document_id: int, data: DocumentUpdate) -> Document:
    d = get_document(db, user, document_id)
    changes = data.model_dump(exclude_unset=True)
    _check_refs(db, user, changes.get("project_id"), changes.get("source_id"))
    for k, v in changes.items():
        setattr(d, k, v)
    activity.record(db, user=user, actor="user", action="document.update", entity_type="document", entity_id=d.id,
                    summary=f"Modificati i metadati di «{d.title}»")
    db.commit()
    db.refresh(d)
    return d


def delete_document(db: Session, user: User, settings: Settings, document_id: int, confirm: bool) -> None:
    d = get_document(db, user, document_id)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un documento dall'archivio richiede conferma (confirm=true).")
    path = settings.data_dir / d.storage_path
    title = d.title
    index.fts_delete_document(db, d.id)
    db.delete(d)
    activity.record(db, user=user, actor="user", action="document.delete", entity_type="document", entity_id=document_id,
                    summary=f"Eliminato il documento «{title}»")
    db.commit()
    index.semantic_index.invalidate(user.id)
    if path.is_file() and path.resolve().is_relative_to(settings.data_dir.resolve()):
        path.unlink()


def file_path(settings: Settings, d: Document) -> Path:
    p = (settings.data_dir / d.storage_path).resolve()
    if not p.is_relative_to(settings.data_dir.resolve()) or not p.is_file():
        raise NotFoundError("File originale non disponibile.")
    return p
