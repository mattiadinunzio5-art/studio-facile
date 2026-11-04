"""Hash delle password con scrypt (libreria standard, nessuna dipendenza esterna)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

N, R, P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False


def password_problems(password: str, email: str = "") -> list[str]:
    problems = []
    if len(password) < 10:
        problems.append("almeno 10 caratteri")
    if password.isdigit() or password.isalpha():
        problems.append("lettere e numeri o simboli")
    if len(set(password)) < 5:
        problems.append("almeno 5 caratteri diversi")
    if email and email.split("@")[0].lower() in password.lower():
        problems.append("non deve contenere il nome dell'email")
    return problems
