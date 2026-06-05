"""Persistência do histórico de preços em JSON."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .logger import get_logger

log = get_logger(__name__)


class History:
    """Lê/grava o histórico de melhores preços por destino."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            log.info("Histórico inexistente; iniciando vazio (%s).", self.path)
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                return json.load(fh) or {}
        except (json.JSONDecodeError, OSError) as exc:
            log.error("Falha ao ler histórico (%s): %s. Iniciando vazio.", self.path, exc)
            return {}

    def last_price(self, dest_id: str) -> float | None:
        entry = self._data.get(dest_id)
        return entry.get("price") if entry else None

    def update(self, dest_id: str, offer: dict[str, Any]) -> None:
        """Atualiza o registro do destino com a nova melhor oferta."""
        record = self._data.setdefault(dest_id, {"runs": []})
        record["price"] = offer["price"]
        record["currency"] = offer.get("currency", "")
        record["details"] = offer.get("details", "")
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        record.setdefault("runs", []).append(
            {"price": offer["price"], "at": record["updated_at"]}
        )
        # Mantém apenas as últimas 50 execuções por destino.
        record["runs"] = record["runs"][-50:]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)
        tmp.replace(self.path)  # escrita atômica
        log.info("Histórico salvo em %s.", self.path)
