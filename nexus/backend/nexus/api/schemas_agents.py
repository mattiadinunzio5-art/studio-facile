"""Schemi API — AI Research / War Room (Fase 5)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from .schemas import CleanStr, ORMModel, UTCDateTime


class RunCreate(BaseModel):
    question: Annotated[CleanStr, StringConstraints(min_length=5, max_length=2000)]
    project_id: int | None = None
    document_ids: list[int] | None = Field(default=None, max_length=50)
    series_ids: list[int] | None = Field(default=None, max_length=8)


class StepOut(ORMModel):
    ordinal: int
    agent: str
    status: Literal["executed", "skipped", "failed"]
    executor: Literal["local", "ai", "none"]
    provider: str
    model: str
    summary: str
    output: dict
    issues: list
    error: str | None
    duration_ms: int
    input_tokens: int | None
    output_tokens: int | None


class RunOut(ORMModel):
    id: int
    question: str
    status: str
    mode: Literal["local", "ai"]
    provider: str
    model: str
    project_id: int | None
    plan: dict
    evidence: list
    result: dict
    error: str | None
    decision_note: str
    decided_at: UTCDateTime | None
    finished_at: UTCDateTime | None
    created_at: UTCDateTime
    steps: list[StepOut]


class RunSummary(ORMModel):
    id: int
    question: str
    status: str
    mode: str
    provider: str
    created_at: UTCDateTime


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    note: Annotated[CleanStr, StringConstraints(max_length=2000)] = ""
    accepted_relations: list[int] = Field(default_factory=list, description="Indici delle relazioni proposte da salvare come ipotesi AI")


class ProviderSelectIn(BaseModel):
    provider: Literal["none", "ollama", "openai-compatible", "anthropic"]
    effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
