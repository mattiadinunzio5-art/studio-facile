"""Modelli ORM. Importare da qui per registrare tutte le tabelle nei metadata."""

from .activity import ActivityLog
from .connector import ConnectorState
from .document import Document, DocumentChunk
from .notification import Notification
from .preference import UserPreference
from .project import Project
from .search import SearchQuery
from .source import Source
from .user import User

__all__ = [
    "ActivityLog",
    "ConnectorState",
    "Document",
    "DocumentChunk",
    "Notification",
    "Project",
    "SearchQuery",
    "Source",
    "User",
    "UserPreference",
]
