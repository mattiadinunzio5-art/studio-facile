"""Schemi API — Research Studio e Daily Briefing (Fase 7)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from .schemas import CleanStr, ORMModel, UTCDateTime


class SeriesEmbed(BaseModel):
    type: Literal["series"]
    series_id: int
    caption: Annotated[CleanStr, StringConstraints(max_length=300)] = ""


class SimulationEmbed(BaseModel):
    type: Literal["simulation"]
    simulation_id: int
    caption: Annotated[CleanStr, StringConstraints(max_length=300)] = ""


class TableEmbed(BaseModel):
    type: Literal["table"]
    caption: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    columns: list[Annotated[str, StringConstraints(max_length=100)]] = Field(min_length=1, max_length=12)
    rows: list[list[Annotated[str, StringConstraints(max_length=300)]]] = Field(max_length=200)

    @field_validator("rows")
    @classmethod
    def _width(cls, rows, info):
        n = len(info.data.get("columns", []))
        if any(len(r) != n for r in rows):
            raise ValueError("Ogni riga della tabella deve avere lo stesso numero di colonne dell'intestazione")
        return rows


Embed = Annotated[SeriesEmbed | SimulationEmbed | TableEmbed, Field(discriminator="type")]


class ReportCreate(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    subtitle: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    author: Annotated[CleanStr, StringConstraints(max_length=200)] = ""
    project_id: int | None = None


class ReportUpdate(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)] | None = None
    subtitle: Annotated[CleanStr, StringConstraints(max_length=300)] | None = None
    author: Annotated[CleanStr, StringConstraints(max_length=200)] | None = None
    project_id: int | None = None
    source_ids: list[int] | None = Field(default=None, max_length=500)


class SectionIn(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)] | None = None
    body: Annotated[str, StringConstraints(max_length=200_000)] | None = None
    embeds: list[Embed] | None = Field(default=None, max_length=20)


class ChapterIn(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    after_key: str = "analysis"


class SectionOut(ORMModel):
    id: int
    ordinal: int
    key: str
    title: str
    body: str
    embeds: list


class ReportOut(ORMModel):
    id: int
    title: str
    subtitle: str
    author: str
    status: Literal["draft", "approved"]
    project_id: int | None
    source_ids: list[int]
    origin: str
    contains_ai_text: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime
    sections: list[SectionOut]


class ReportSummary(ORMModel):
    id: int
    title: str
    status: str
    project_id: int | None
    origin: str
    updated_at: UTCDateTime


class ReportCheck(BaseModel):
    ready: bool
    empty_sections: list[str]
    invalid_citations: list[int]
    unverified_sources: list[dict]
    cited_sources: int
    bibliography_size: int
    embed_problems: list[str]
    warnings: list[str]


class NoteIn(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    body: Annotated[str, StringConstraints(max_length=100_000)] = ""
    project_id: int | None = None
    source_id: int | None = None
    document_id: int | None = None


class NoteOut(ORMModel):
    id: int
    title: str
    body: str
    project_id: int | None
    source_id: int | None
    document_id: int | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class BriefingIn(BaseModel):
    refresh_sources: bool = False


class BriefingOut(ORMModel):
    id: int
    trigger: str
    content: dict
    created_at: UTCDateTime
