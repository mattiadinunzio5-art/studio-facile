"""Configurazione centralizzata.

Tutti i valori sono letti da variabili d'ambiente con prefisso ``NEXUS_`` (o da
``nexus/.env``). Nessun servizio esterno è obbligatorio.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# nexus/backend/nexus/core/config.py -> nexus/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "nexus.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["development", "test", "production"] = "development"
    database_url: str = Field(default=f"sqlite:///{DEFAULT_DB_PATH}")
    auto_migrate: bool = True
    log_level: str = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )
    # Timeout (secondi) per i controlli di raggiungibilità delle fonti esterne.
    connector_timeout: float = 6.0
    # Provider AI: "none" finché l'utente non configura volontariamente credenziali.
    ai_provider: str = "none"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def database_label(self) -> str:
        """Descrizione del database senza credenziali."""
        if self.is_sqlite:
            return "SQLite"
        scheme = self.database_url.split(":", 1)[0]
        return scheme.split("+", 1)[0].capitalize()


@lru_cache
def get_settings() -> Settings:
    return Settings()
