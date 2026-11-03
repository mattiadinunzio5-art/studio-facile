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

    # Cartella dei dati locali (file importati, cache dei connettori, chiave segreta).
    data_dir: Path = Field(default=PROJECT_ROOT / "data")
    max_upload_mb: int = 25
    # Motore di embedding: "lsa" (predefinito, scikit-learn) o "sentence-transformers".
    embeddings: Literal["lsa", "sentence-transformers"] = "lsa"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # Chiave per cifrare le credenziali salvate (generata in data_dir se assente).
    secret_key: str | None = None
    # Cache dei connettori (ore) prima di riscaricare una serie.
    connector_cache_hours: int = 24
    # Autenticazione: "local" = utente unico locale; "multi" = account con login.
    auth_mode: Literal["local", "multi"] = "local"
    session_hours: int = 24 * 7
    # Limiti alle operazioni automatiche.
    max_agent_steps: int = 12

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

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
