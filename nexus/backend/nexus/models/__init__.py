"""Modelli ORM. Importare da qui per registrare tutte le tabelle nei metadata."""

from .activity import ActivityLog
from .connector import ConnectorState
from .notification import Notification
from .preference import UserPreference
from .project import Project
from .search import SearchQuery
from .user import User

__all__ = [
    "ActivityLog",
    "ConnectorState",
    "Notification",
    "Project",
    "SearchQuery",
    "User",
    "UserPreference",
]
