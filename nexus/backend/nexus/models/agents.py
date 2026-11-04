from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base, TimestampMixin, utcnow

RUN_STATUSES = ("queued", "running", "awaiting_approval", "approved", "rejected", "failed")
AGENTS = ("planner", "researcher", "historian", "economist", "quant", "skeptic", "synthesizer")


class ResearchRun(TimestampMixin, Base):
    """Esecuzione del flusso multi-agente:
    domanda → pianificazione → ricerca → analisi → controanalisi → sintesi → approvazione."""

    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False)  # local | ai
    provider: Mapped[str] = mapped_column(String(40), default="none", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    options: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list["AgentStep"]] = relationship(cascade="all, delete-orphan", passive_deletes=True, order_by="AgentStep.ordinal")


class AgentStep(Base):
    """Passo di un agente. ``executor`` dice se ha lavorato un modello AI o il motore locale;
    ``skipped`` indica esplicitamente un agente non eseguito (mai simulato)."""

    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    agent: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # executed | skipped | failed
    executor: Mapped[str] = mapped_column(String(10), nullable=False)  # local | ai | none
    provider: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    issues: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
