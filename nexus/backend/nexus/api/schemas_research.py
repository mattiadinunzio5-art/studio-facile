"""Schemi API — Research Core (Fase 2)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from ..research.citations import normalize_doi, valid_doi, valid_isbn, valid_url
from .schemas import CleanStr, ORMModel, UTCDateTime

SourceType = Literal["book", "article", "chapter", "web", "dataset", "archive", "document", "other"]
VerificationStatus = Literal["unverified", "verified_user", "verified_registry", "not_found"]


class SourceIn(BaseModel):
    source_type: SourceType = "other"
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=500)]
    authors: list[Annotated[CleanStr, StringConstraints(min_length=1, max_length=200)]] = Field(default_factory=list, max_length=50)
    year: int | None = Field(default=None, ge=-3000, le=2100)
    publisher: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    container: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    pages: Annotated[CleanStr, StringConstraints(max_length=50)] = ""
    doi: Annotated[CleanStr, StringConstraints(max_length=200)] = ""
    isbn: Annotated[CleanStr, StringConstraints(max_length=20)] = ""
    url: Annotated[CleanStr, StringConstraints(max_length=1000)] = ""
    accessed_at: Annotated[CleanStr, StringConstraints(max_length=10, pattern=r"^(\d{4}-\d{2}-\d{2})?$")] = ""
    notes: Annotated[CleanStr, StringConstraints(max_length=5000)] = ""

    @field_validator("doi")
    @classmethod
    def _doi(cls, v: str) -> str:
        if v and not valid_doi(v):
            raise ValueError("DOI non valido (formato atteso 10.xxxx/...)")
        return normalize_doi(v) if v else v

    @field_validator("isbn")
    @classmethod
    def _isbn(cls, v: str) -> str:
        if v and not valid_isbn(v):
            raise ValueError("ISBN non valido (cifra di controllo errata)")
        return v

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        if v and not valid_url(v):
            raise ValueError("URL non valido (deve iniziare con http:// o https://)")
        return v


class SourceOut(ORMModel):
    id: int
    source_type: str
    title: str
    authors: list[str]
    year: int | None
    publisher: str
    container: str
    pages: str
    doi: str
    isbn: str
    url: str
    accessed_at: str
    notes: str
    verification_status: VerificationStatus
    verification_note: str
    verified_at: UTCDateTime | None
    is_demo: bool
    citation: str = ""
    created_at: UTCDateTime


class SourceVerifyIn(BaseModel):
    method: Literal["user", "registry"]
    note: Annotated[CleanStr, StringConstraints(max_length=1000)] = ""


class DocumentOut(ORMModel):
    id: int
    title: str
    filename: str
    kind: str
    category: str
    origin: str
    origin_url: str
    license_note: str
    author: str
    year: int | None
    sha256: str
    size_bytes: int
    page_count: int | None
    char_count: int
    chunk_count: int
    status: str
    error: str | None
    flagged_chunks: int
    project_id: int | None
    source_id: int | None
    is_demo: bool
    created_at: UTCDateTime


class DocumentUpdate(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)] | None = None
    category: Literal["source_material", "user_work", "dataset"] | None = None
    author: Annotated[CleanStr, StringConstraints(max_length=300)] | None = None
    year: int | None = Field(default=None, ge=-3000, le=2100)
    project_id: int | None = None
    source_id: int | None = None
    license_note: Annotated[CleanStr, StringConstraints(max_length=2000)] | None = None


class ChunkOut(ORMModel):
    id: int
    ordinal: int
    page: int | None
    locator: str
    text: str
    injection_flag: bool


class GutenbergImportIn(BaseModel):
    ebook_id: int = Field(ge=1, le=10_000_000)
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    author: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    project_id: int | None = None


class RetrievalHit(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    page: int | None
    locator: str
    text: str
    score: float
    support: Literal["strong", "partial", "weak", "none"]
    injection_flag: bool
    source_label: str


class RetrievalOut(BaseModel):
    query: str
    mode: Literal["hybrid", "text", "semantic"]
    semantic_engine: str
    hits: list[RetrievalHit]


class AskIn(BaseModel):
    question: Annotated[CleanStr, StringConstraints(min_length=3, max_length=1000)]
    document_ids: list[int] | None = None
    limit: int = Field(default=8, ge=1, le=30)
    use_ai: bool = False


class Claim(BaseModel):
    type: Literal["documented_fact", "interpretation", "hypothesis", "estimate", "missing"]
    text: str
    support: Literal["strong", "partial", "weak", "none"]
    coverage: float = 0.0
    evidence: list[int]
    note: str = ""


class AskOut(BaseModel):
    question: str
    mode: Literal["local_extractive", "ai_grounded"]
    provider: str
    claims: list[Claim]
    passages: list[RetrievalHit]
    disclaimer: str
    issues: list[str] = Field(default_factory=list)
    model: str = ""
