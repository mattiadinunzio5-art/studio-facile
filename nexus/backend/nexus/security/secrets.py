"""Cifratura delle credenziali salvate.

La chiave proviene da ``NEXUS_SECRET_KEY`` oppure da ``<data_dir>/secret.key``
(generata al primo uso con permessi 600). Le credenziali non vengono mai
restituite in chiaro dalle API: solo un suggerimento (ultime 4 cifre).
"""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from ..core.config import Settings


def _key(settings: Settings) -> bytes:
    if settings.secret_key:
        return base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    path: Path = settings.data_dir / "secret.key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(Fernet.generate_key())
    return path.read_bytes().strip()


def encrypt(settings: Settings, value: str) -> str:
    return Fernet(_key(settings)).encrypt(value.encode()).decode()


def decrypt(settings: Settings, token: str) -> str | None:
    if not token:
        return None
    try:
        return Fernet(_key(settings)).decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def hint(value: str) -> str:
    return f"…{value[-4:]}" if len(value) >= 8 else "…"
