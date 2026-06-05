"""Base do sistema de provedores plugável.

Para adicionar um novo provedor:
1. Crie um arquivo em src/providers/ (ex.: amadeus.py).
2. Crie uma classe que herde de Provider.
3. Decore-a com @register("nome_usado_no_yaml").
4. Implemente fetch_offers(). Pronto — o registry detecta automaticamente.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Callable

from ..logger import get_logger

log = get_logger(__name__)

# Registro global: nome -> classe do provedor
_REGISTRY: dict[str, type["Provider"]] = {}


@dataclass
class Offer:
    """Uma oferta normalizada, independente do provedor."""

    price: float
    currency: str = "BRL"
    details: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"price": self.price, "currency": self.currency, "details": self.details}


class Provider(abc.ABC):
    """Interface comum a todos os provedores."""

    #: tipo lógico (flight/hotel/bus) — informativo
    kind: str = "generic"

    @abc.abstractmethod
    def fetch_offers(self, params: dict[str, Any]) -> list[Offer]:
        """Consulta a fonte e retorna ofertas. Pode levantar exceção em erro."""
        raise NotImplementedError

    def best_offer(self, params: dict[str, Any]) -> Offer | None:
        """Retorna a oferta de menor preço, ou None se não houver."""
        offers = self.fetch_offers(params)
        if not offers:
            return None
        return min(offers, key=lambda o: o.price)


def register(name: str) -> Callable[[type[Provider]], type[Provider]]:
    """Decorator que registra um provedor pelo nome usado no YAML."""

    def _wrap(cls: type[Provider]) -> type[Provider]:
        key = name.lower()
        if key in _REGISTRY:
            log.warning("Provedor '%s' já registrado; sobrescrevendo.", key)
        _REGISTRY[key] = cls
        return cls

    return _wrap


def get_provider(name: str) -> Provider:
    """Instancia um provedor registrado pelo nome."""
    key = name.lower()
    if key not in _REGISTRY:
        raise KeyError(
            f"Provedor '{name}' não registrado. Disponíveis: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[key]()


def available_providers() -> list[str]:
    return sorted(_REGISTRY)
