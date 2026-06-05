"""Provedor de demonstração (mock).

Gera preços pseudo-aleatórios determinísticos por dia, úteis para testar o
fluxo completo sem chaves de API nem custo. Use como referência para escrever
provedores reais.
"""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from .base import Offer, Provider, register


def _pseudo_price(seed: str, low: float, high: float) -> float:
    """Preço estável dentro do dia, variando entre execuções de dias diferentes."""
    today = date.today().isoformat()
    digest = hashlib.sha256(f"{seed}|{today}".encode()).hexdigest()
    frac = int(digest[:8], 16) / 0xFFFFFFFF
    return round(low + frac * (high - low), 2)


@register("mock")
class MockProvider(Provider):
    kind = "mock"

    def fetch_offers(self, params: dict[str, Any]) -> list[Offer]:
        seed = "|".join(f"{k}={v}" for k, v in sorted(params.items()))
        base = _pseudo_price(seed, 90.0, 600.0)
        # Algumas "companhias" com pequenas variações.
        return [
            Offer(price=round(base * 1.00, 2), currency="BRL", details="Opção A (mock)"),
            Offer(price=round(base * 1.12, 2), currency="BRL", details="Opção B (mock)"),
            Offer(price=round(base * 0.95, 2), currency="BRL", details="Opção C (mock)"),
        ]
