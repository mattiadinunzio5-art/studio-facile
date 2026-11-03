"""Schemi Pydantic delle API (contratto condiviso con il frontend)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def _as_utc(value: datetime) -> datetime:
    # SQLite non conserva il fuso: i valori salvati sono sempre UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]
CleanStr = Annotated[str, StringConstraints(strip_whitespace=True)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Sistema -----------------------------------------------------------------


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str


class AIProviderOut(BaseModel):
    id: str
    name: str
    kind: str
    requires_credentials: bool
    implemented: bool
    notes: str


class SystemStatusOut(BaseModel):
    version: str
    environment: str
    database: str
    database_ok: bool
    ai_mode: Literal["local", "remote"]
    ai_provider: AIProviderOut
    ai_providers: list[AIProviderOut]
    server_time: UTCDateTime


class UserOut(ORMModel):
    id: int
    email: str
    display_name: str
    role: str
    plan: str
    is_local: bool


# --- Moduli ------------------------------------------------------------------


class ModuleOut(BaseModel):
    id: str
    code: str
    name: str
    summary: str
    phase: int
    status: Literal["in_preparation", "partial", "available"]
    planned_features: list[str]
    implemented_features: list[str]


# --- Progetti ----------------------------------------------------------------

ProjectStatus = Literal["active", "archived"]


class ProjectCreate(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=200)]
    description: Annotated[CleanStr, StringConstraints(max_length=5000)] = ""


class ProjectUpdate(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=200)] | None = None
    description: Annotated[CleanStr, StringConstraints(max_length=5000)] | None = None
    status: ProjectStatus | None = None


class ProjectOut(ORMModel):
    id: int
    title: str
    description: str
    status: ProjectStatus
    is_demo: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime


# --- Attività / notifiche / ricerca --------------------------------------------


class ActivityOut(ORMModel):
    id: int
    actor: str
    action: str
    entity_type: str | None
    entity_id: str | None
    summary: str
    created_at: UTCDateTime


class NotificationOut(ORMModel):
    id: int
    level: Literal["info", "warning", "error"]
    title: str
    body: str
    read_at: UTCDateTime | None
    created_at: UTCDateTime


class SearchQueryOut(ORMModel):
    id: int
    query: str
    results_count: int
    created_at: UTCDateTime


class SearchHit(BaseModel):
    type: Literal["project", "module", "document", "event", "entity", "series", "report"]
    id: str
    title: str
    snippet: str
    url: str


class SearchResultOut(BaseModel):
    query: str
    hits: list[SearchHit]
    searched_scopes: list[str]
    unavailable_scopes: list[str]


# --- Connettori --------------------------------------------------------------


class ConnectorOut(BaseModel):
    id: str
    name: str
    category: str
    homepage: str
    terms_url: str
    requires_api_key: bool
    implemented: bool
    planned_phase: int
    notes: str
    last_status: Literal["unknown", "reachable", "degraded", "unreachable"]
    last_checked_at: UTCDateTime | None
    last_http_status: int | None
    last_latency_ms: int | None
    last_error: str | None


# --- Preferenze dashboard -----------------------------------------------------

WidgetId = Literal[
    "modules",
    "sources",
    "searches",
    "projects",
    "indicators",
    "events",
    "reports",
    "ai",
    "notifications",
]
ALL_WIDGETS: list[str] = list(WidgetId.__args__)  # type: ignore[attr-defined]


class DashboardLayout(BaseModel):
    order: list[WidgetId] = Field(default_factory=lambda: list(ALL_WIDGETS))
    hidden: list[WidgetId] = Field(default_factory=list)


# --- Dashboard ---------------------------------------------------------------


class UnavailableSection(BaseModel):
    """Sezione priva di dati reali: lo dichiara esplicitamente."""

    available: Literal[False] = False
    reason: str
    planned_phase: int


class SourcesSummary(BaseModel):
    total: int
    implemented: int
    by_status: dict[str, int]
    items: list[ConnectorOut]


class ProjectsSummary(BaseModel):
    active_count: int
    archived_count: int
    items: list[ProjectOut]


class AIActivity(BaseModel):
    mode: Literal["local", "remote"]
    provider: str
    runs: list[dict]
    note: str


class NotificationsSummary(BaseModel):
    unread_count: int
    items: list[NotificationOut]


class DashboardOut(BaseModel):
    generated_at: UTCDateTime
    layout: DashboardLayout
    modules: list[ModuleOut]
    sources: SourcesSummary
    recent_searches: list[SearchQueryOut]
    projects: ProjectsSummary
    indicators: UnavailableSection
    events: UnavailableSection
    reports: UnavailableSection
    ai: AIActivity
    notifications: NotificationsSummary
    recent_activity: list[ActivityOut]
