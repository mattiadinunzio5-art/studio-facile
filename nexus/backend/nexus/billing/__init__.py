"""Predisposizione per i pagamenti (nessun pagamento reale attivo)."""

from __future__ import annotations

from typing import Protocol


class PaymentNotConfigured(Exception):
    pass


class PaymentProvider(Protocol):
    id: str

    def create_checkout(self, user_id: int, plan_id: str) -> str:
        """Restituisce l'URL di pagamento del fornitore."""

    def handle_webhook(self, payload: bytes, signature: str) -> dict:
        """Verifica la firma e restituisce l'evento normalizzato (es. piano attivato)."""


class NullPaymentProvider:
    """Fornitore predefinito: dichiara esplicitamente che i pagamenti non sono attivi."""

    id = "none"

    def create_checkout(self, user_id: int, plan_id: str) -> str:
        raise PaymentNotConfigured("Pagamenti non attivi: nessun fornitore configurato. Il piano viene assegnato da un amministratore.")

    def handle_webhook(self, payload: bytes, signature: str) -> dict:
        raise PaymentNotConfigured("Pagamenti non attivi.")


def get_provider() -> PaymentProvider:
    return NullPaymentProvider()
