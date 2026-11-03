"""Modelli ORM. Importare da qui per registrare tutte le tabelle nei metadata."""

from .activity import ActivityLog
from .agents import AgentStep, ResearchRun
from .connector import ConnectorState
from .finance import Credential, Observation, Series
from .document import Document, DocumentChunk
from .graph import Entity, Relation
from .lab import SimulationRun
from .history import EventSource, HistoricalEvent, KnowledgeItem
from .notification import Notification
from .preference import UserPreference
from .project import Project
from .search import SearchQuery
from .source import Source
from .studio import Briefing, Note, Report, ReportSection
from .user import User

__all__ = [
    "ActivityLog",
    "Briefing",
    "Note",
    "Report",
    "ReportSection",
    "AgentStep",
    "ResearchRun",
    "ConnectorState",
    "Credential",
    "Observation",
    "Series",
    "Document",
    "DocumentChunk",
    "Entity",
    "EventSource",
    "HistoricalEvent",
    "KnowledgeItem",
    "Relation",
    "Notification",
    "Project",
    "SearchQuery",
    "SimulationRun",
    "Source",
    "User",
    "UserPreference",
]
