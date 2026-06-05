"""Pacote de provedores.

Importa automaticamente todos os módulos desta pasta para que os decorators
@register sejam executados e os provedores fiquem disponíveis no registry.
Basta criar um novo arquivo .py aqui — ele será carregado sem alterar mais nada.
"""
from __future__ import annotations

import importlib
import pkgutil

from . import base  # reexporta o registry

# Importa dinamicamente todos os submódulos (exceto 'base').
for _mod in pkgutil.iter_modules(__path__):
    if _mod.name != "base":
        importlib.import_module(f"{__name__}.{_mod.name}")

get_provider = base.get_provider
available_providers = base.available_providers
Offer = base.Offer
Provider = base.Provider
register = base.register

__all__ = [
    "get_provider",
    "available_providers",
    "Offer",
    "Provider",
    "register",
]
