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


AI_DISCLAIMER = (
    "Risposta generata da un modello AI a partire SOLO dai passaggi recuperati. Ogni affermazione è stata controllata: "
    "quelle presentate come fatti senza evidenze adeguate sono state declassate. Verifica sempre le fonti citate."
)


def ask(db: Session, user: User, settings: Settings, question: str, document_ids: list[int] | None, limit: int, use_ai: bool = False) -> AskOut:
    passages, _ = retrieve(db, user, settings, question, "hybrid", limit, document_ids)
    if use_ai:
        return _ask_ai(db, user, settings, question, passages)
    claims = extract_claims(question, passages)
    return AskOut(
        question=question,
        mode="local_extractive",
        provider="none",
        claims=[Claim(**c) for c in claims],
        passages=[to_hit(question, p) for p in passages],
        disclaimer=LOCAL_DISCLAIMER,
    )


def _ask_ai(db: Session, user: User, settings: Settings, question: str, passages) -> AskOut:
    from ..agents import guard, llm, prompts
    from ..core.errors import ValidationFailedError
    from ..research.safety import wrap_untrusted
    from . import ai

    try:
        client = ai.client_for(db, user, settings)
    except llm.ProviderError as exc:
        raise ValidationFailedError(str(exc)) from exc
    if client is None:
        raise ValidationFailedError("Nessun provider AI configurato: usa la risposta locale o configura un provider in Sistema.")
    hits = [to_hit(question, p) for p in passages]
    if not passages:
        return AskOut(question=question, mode="ai_grounded", provider=client.provider, model=client.model, passages=[],
                      claims=[Claim(type="missing", text="Nessun passaggio dell'archivio risponde alla domanda.", support="none", evidence=[])],
                      disclaimer=AI_DISCLAIMER + " Il modello non è stato interrogato perché non c'erano evidenze.")
    ids = {f"E{i}": p for i, p in enumerate(passages, start=1)}
    block = "\n".join(wrap_untrusted(k, f"{p.document_title}, {p.locator}", p.text) for k, p in ids.items())
    try:
        res = client.complete(prompts.ROLES["synthesizer"], f"Domanda: {question}\n\nEvidenze:\n{block}")
        data = guard.parse_json(res.text)
    except (llm.ProviderError, guard.ParseError) as exc:
        raise ValidationFailedError(f"Risposta AI non disponibile: {exc}") from exc
    claims, issues = guard.validate_claims(data.get("claims"), {k: {"text": p.text} for k, p in ids.items()})
    chunk_of = {k: p.chunk_id for k, p in ids.items()}
    for c in claims:
        c["evidence"] = [chunk_of[e] for e in c["evidence"]]
    from . import activity

    activity.record(db, user=user, actor="ai", action="research.ask_ai", summary=f"Domanda all'archivio con {client.provider}: «{question[:80]}»")
    db.commit()
    return AskOut(question=question, mode="ai_grounded", provider=client.provider, model=res.model, claims=[Claim(**c) for c in claims],
                  passages=hits, disclaimer=AI_DISCLAIMER, issues=issues + res.notes)
