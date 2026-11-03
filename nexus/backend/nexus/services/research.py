"""Ricerca nell'archivio e risposte con citazioni."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_research import AskOut, Claim, RetrievalHit, RetrievalOut
from ..core.config import Settings
from ..models import Document, DocumentChunk, Source, User
from ..research import index
from ..research.answer import Passage, coverage, extract_claims, support_level
from ..research.citations import format_citation


def _semantic(db: Session, user: User, settings: Settings, q: str, limit: int) -> tuple[list, str]:
    if settings.embeddings == "sentence-transformers":
        try:
            emb = index.NeuralEmbedder(settings.embedding_model)
            res = index.neural_search(db, user.id, emb, q, limit)
            if res:
                return res, f"sentence-transformers ({settings.embedding_model})"
        except RuntimeError:
            pass
    return index.semantic_index.search_lsa(db, user.id, q, limit), "LSA (TF-IDF + SVD, scikit-learn)"


def retrieve(
    db: Session, user: User, settings: Settings, q: str, mode: str = "hybrid", limit: int = 10, document_ids: list[int] | None = None
) -> tuple[list[Passage], str]:
    pool = max(limit * 4, 30)
    engine = "nessuno"
    rankings = []
    if mode in ("hybrid", "text"):
        rankings.append(index.text_search(db, user.id, q, pool, document_ids))
    if mode in ("hybrid", "semantic"):
        sem, engine = _semantic(db, user, settings, q, pool)
        if document_ids:
            allowed = set(
                db.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id.in_(document_ids), DocumentChunk.owner_id == user.id))
            )
            sem = [x for x in sem if x[0] in allowed]
        rankings.append(sem)
    fused = index.rrf(rankings)[:limit] if mode == "hybrid" else (rankings[0][:limit] if rankings else [])
    if not fused:
        return [], engine
    ids = [cid for cid, _ in fused]
    rows = db.execute(
        select(DocumentChunk, Document, Source)
        .join(Document, Document.id == DocumentChunk.document_id)
        .outerjoin(Source, Source.id == Document.source_id)
        .where(DocumentChunk.id.in_(ids), DocumentChunk.owner_id == user.id)
    ).all()
    by_id = {c.id: (c, d, s) for c, d, s in rows}
    passages = []
    for cid, score in fused:
        if cid not in by_id:
            continue
        c, d, s = by_id[cid]
        label = format_citation(s) if s else f"{d.title}" + (f" — {d.author}" if d.author else "") + " [documento senza scheda bibliografica]"
        passages.append(Passage(c.id, d.id, d.title, c.page, c.locator, c.text, round(score, 4), c.injection_flag, label))
    return passages, engine


def to_hit(q: str, p: Passage) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=p.chunk_id, document_id=p.document_id, document_title=p.document_title, page=p.page, locator=p.locator,
        text=p.text, score=p.score, support=support_level(coverage(q, p.text)), injection_flag=p.injection_flag,
        source_label=p.source_label,
    )


def search(db: Session, user: User, settings: Settings, q: str, mode: str, limit: int) -> RetrievalOut:
    passages, engine = retrieve(db, user, settings, q, mode, limit)
    return RetrievalOut(query=q, mode=mode, semantic_engine=engine if mode != "text" else "—", hits=[to_hit(q, p) for p in passages])


LOCAL_DISCLAIMER = (
    "Modalità locale: nessun modello AI è stato usato. Le affermazioni sono frasi estratte alla lettera dai "
    "documenti, con la loro collocazione. Interpretazioni, ipotesi e stime non vengono generate."
)


def ask(db: Session, user: User, settings: Settings, question: str, document_ids: list[int] | None, limit: int) -> AskOut:
    passages, _ = retrieve(db, user, settings, question, "hybrid", limit, document_ids)
    claims = extract_claims(question, passages)
    return AskOut(
        question=question,
        mode="local_extractive",
        provider="none",
        claims=[Claim(**c) for c in claims],
        passages=[to_hit(question, p) for p in passages],
        disclaimer=LOCAL_DISCLAIMER,
    )
