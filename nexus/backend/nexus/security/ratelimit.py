"""Limite ai tentativi di accesso falliti (in memoria, per processo)."""

from __future__ import annotations

import threading
import time


class LoginLimiter:
    def __init__(self, max_failures: int = 5, window_seconds: int = 900):
        self.max, self.window = max_failures, window_seconds
        self._fails: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> list[float]:
        items = [t for t in self._fails.get(key, []) if now - t < self.window]
        self._fails[key] = items
        return items

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.time())) >= self.max

    def fail(self, key: str) -> None:
        with self._lock:
            self._prune(key, time.time()).append(time.time())

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)
