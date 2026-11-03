"""Schemi API — Historical Intelligence, Time Machine, Knowledge Graph (Fase 3)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from ..history import dates
from .schemas import CleanStr, ORMModel, UTCDateTime

Category = Literal["economic", "monetary", "banking", "industrial", "war_geopolitics", "revolution", "financial_crisis", "empires", "capitalism"]
Reliability = Literal["established", "probable", "disputed", "unverified"]
KnowledgeKind = Literal["contemporary", "later_discovery", "archival_release", "historiography"]
EntityType = Literal["person", "state", "company", "bank", "institution", "event", "document", "theory", "indicator"]
RelationType = Literal["caused", "influenced", "contemporary_of", "related_to", "financed", "involved_in", "replaced", "preceded"]
Provenance = Literal["sourced", "user_hypothesis", "ai_hypothesis"]
Short = Annotated[CleanStr, StringConstraints(min_length=1, max_length=200)]
LongText = Annotated[CleanStr, StringConstraints(max_length=20000)]


class EventIn(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    start_year: int
    start_month: int | None = None
    start_day: int | None = None
    end_year: int | None = None
    end_month: int | None = None
    end_day: int | None = None
    period: Annotated[CleanStr, StringConstraints(max_length=120)] = ""
    region: Annotated[CleanStr, StringConstraints(max_length=120)] = ""
    countries: list[Short] = Field(default_factory=list, max_length=60)
    categories: list[Category] = Field(default_factory=list)
    description: LongText = ""
    causes: LongText = ""
    consequences: LongText = ""
    people: list[Short] = Field(default_factory=list, max_length=100)
    institutions: list[Short] = Field(default_factory=list, max_length=100)
    economic_implications: LongText = ""
    reliability: Reliability = "unverified"
    reliability_note: Annotated[CleanStr, StringConstraints(max_length=2000)] = ""

    @model_validator(mode="after")
    def _dates(self):
        dates.validate(self.start_year, self.start_month, self.start_day, "Data iniziale")
        dates.validate(self.end_year, self.end_month, self.end_day, "Data finale")
        if self.end_year is not None and dates.sort_key(self.end_year, self.end_month, self.end_day) < dates.sort_key(
            self.start_year, self.start_month, self.start_day
        ):
            raise ValueError("La data finale precede quella iniziale")
        self.categories = list(dict.fromkeys(self.categories))
        return self


class EventSourceOut(BaseModel):
    source_id: int
    citation: str
    verification_status: str
    pages: str
    note: str


class KnowledgeIn(BaseModel):
    content: Annotated[CleanStr, StringConstraints(min_length=1, max_length=5000)]
    known_since_year: int = Field(ge=-10000, le=2200)
    kind: KnowledgeKind = "contemporary"
    source_id: int | None = None


class KnowledgeOut(ORMModel):
    id: int
    content: str
    known_since_year: int
    kind: KnowledgeKind
    source_id: int | None


class EventOut(ORMModel):
    id: int
    title: str
    start_year: int
    start_month: int | None
    start_day: int | None
    end_year: int | None
    end_month: int | None
    end_day: int | None
    date_label: str = ""
    period: str
    region: str
    countries: list[str]
    categories: list[str]
    description: str
    causes: str
    consequences: str
    people: list[str]
    institutions: list[str]
    economic_implications: str
    reliability: Reliability
    reliability_note: str
    is_demo: bool
    sources: list[EventSourceOut] = Field(default_factory=list)
    knowledge: list[KnowledgeOut] = Field(default_factory=list)
    entity_id: int | None = None
    source_warning: str | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class EventSourceLinkIn(BaseModel):
    source_id: int
    pages: Annotated[CleanStr, StringConstraints(max_length=50)] = ""
    note: Annotated[CleanStr, StringConstraints(max_length=1000)] = ""


class EventLinkIn(BaseModel):
    target_event_id: int
    relation_type: RelationType
    provenance: Provenance
    source_id: int | None = None
    chunk_id: int | None = None
    evidence_note: Annotated[CleanStr, StringConstraints(max_length=2000)] = ""
    confidence: Literal["low", "medium", "high"] = "medium"


# --- Time Machine --------------------------------------------------------------


class TimelineEvent(BaseModel):
    id: int
    title: str
    date_label: str
    start_year: int
    end_year: int | None
    status_at_date: Literal["concluded", "ongoing", "not_applicable"]
    countries: list[str]
    categories: list[str]
    reliability: str
    description: str
    consequences: str | None
    consequences_hidden: bool
    known_then: list[KnowledgeOut]
    known_later: list[KnowledgeOut]
    hidden_later_count: int
    is_demo: bool


class TimelineIndicator(BaseModel):
    series_id: int
    name: str
    unit: str
    source: str
    last_date: str
    last_value: float
    caveat: str


class TimelineOut(BaseModel):
    as_of_year: int | None
    hindsight: bool
    filters: dict
    events: list[TimelineEvent]
    indicators: list[TimelineIndicator]
    hidden_future_events: int
    notes: list[str]


# --- Knowledge Graph -------------------------------------------------------------


class EntityIn(BaseModel):
    entity_type: EntityType
    name: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    description: Annotated[CleanStr, StringConstraints(max_length=10000)] = ""
    aliases: list[Short] = Field(default_factory=list, max_length=30)
    start_year: int | None = Field(default=None, ge=-10000, le=2200)
    end_year: int | None = Field(default=None, ge=-10000, le=2200)
    document_id: int | None = None

    @model_validator(mode="after")
    def _years(self):
        if self.start_year is not None and self.end_year is not None and self.end_year < self.start_year:
            raise ValueError("Anno finale precedente a quello iniziale")
        return self


class EntityOut(ORMModel):
    id: int
    entity_type: str
    name: str
    description: str
    aliases: list[str]
    start_year: int | None
    end_year: int | None
    event_id: int | None
    document_id: int | None
    is_demo: bool


class RelationIn(BaseModel):
    source_entity_id: int
    target_entity_id: int
    relation_type: RelationType
    provenance: Provenance
    source_id: int | None = None
    chunk_id: int | None = None
    evidence_note: Annotated[CleanStr, StringConstraints(max_length=2000)] = ""
    confidence: Literal["low", "medium", "high"] = "medium"
    start_year: int | None = Field(default=None, ge=-10000, le=2200)

    @model_validator(mode="after")
    def _rules(self):
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("Una relazione deve collegare due entità diverse")
        if self.provenance == "sourced" and self.source_id is None and self.chunk_id is None:
            raise ValueError("Una relazione 'documentata' richiede una fonte o un passaggio di documento")
        if self.provenance == "ai_hypothesis":
            raise ValueError("Le ipotesi AI possono essere create solo dagli agenti di ricerca")
        return self


class RelationOut(ORMModel):
    id: int
    source_entity_id: int
    target_entity_id: int
    relation_type: RelationType
    provenance: Provenance
    source_id: int | None
    chunk_id: int | None
    evidence_note: str
    confidence: str
    start_year: int | None
    ai_run_id: int | None
    evidence_label: str = ""
    created_at: UTCDateTime


class GraphNode(BaseModel):
    id: int
    name: str
    entity_type: str
    x: float
    y: float
    degree: int
    betweenness: float
    is_focus: bool = False


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[RelationOut]
    stats: dict


class PathOut(BaseModel):
    found: bool
    entity_ids: list[int]
    relations: list[RelationOut]
