"""Lógica central: avalia cada destino e decide se deve alertar."""
from __future__ import annotations

from typing import Any

from .config import Config, Destination
from .history import History
from .logger import get_logger
from .providers import get_provider

log = get_logger(__name__)


def _decide_alert(
    dest: Destination,
    price: float,
    previous: float | None,
    min_drop_percent: float,
) -> str | None:
    """Retorna o motivo do alerta, ou None se não houver alerta."""
    reasons = []
    if dest.max_price is not None and price <= dest.max_price:
        reasons.append(f"preço {price:.2f} <= limite {dest.max_price:.2f}")
    if previous is not None and price < previous:
        drop = (previous - price) / previous * 100
        if drop >= min_drop_percent:
            reasons.append(f"queda de {drop:.1f}% (de {previous:.2f} para {price:.2f})")
    return "; ".join(reasons) if reasons else None


def run(config: Config) -> list[dict[str, Any]]:
    """Executa o monitoramento. Retorna a lista de alertas e atualiza o histórico."""
    history = History(config.settings.history_file)
    alerts: list[dict[str, Any]] = []

    for dest in config.destinations:
        log.info("Verificando '%s' (provedor=%s)...", dest.name, dest.provider)
        try:
            provider = get_provider(dest.provider)
            best = provider.best_offer(dest.params)
        except Exception as exc:  # erro isolado por destino
            log.error("Erro ao consultar '%s': %s", dest.name, exc)
            continue

        if best is None:
            log.warning("Sem ofertas para '%s'.", dest.name)
            continue

        previous = history.last_price(dest.id)
        log.info(
            "'%s': melhor preço %.2f %s (anterior: %s)",
            dest.name,
            best.price,
            best.currency,
            f"{previous:.2f}" if previous is not None else "n/a",
        )

        reason = _decide_alert(
            dest, best.price, previous, config.settings.min_drop_percent
        )
        if reason:
            log.info("ALERTA para '%s': %s", dest.name, reason)
            alerts.append(
                {
                    "id": dest.id,
                    "name": dest.name,
                    "price": best.price,
                    "currency": best.currency,
                    "previous": previous,
                    "reason": reason,
                    "details": best.details,
                }
            )

        history.update(dest.id, best.as_dict())

    history.save()
    return alerts
