"""Carregamento e validação da configuração (YAML + variáveis de ambiente)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .logger import get_logger

log = get_logger(__name__)


class ConfigError(Exception):
    """Erro de configuração inválida."""


@dataclass
class EmailConfig:
    enabled: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_addr: str = ""
    to_addrs: list[str] = field(default_factory=list)


@dataclass
class Destination:
    id: str
    type: str
    name: str
    provider: str
    params: dict[str, Any]
    max_price: float | None = None


@dataclass
class Settings:
    history_file: str = "data/history.json"
    log_dir: str = "logs"
    log_level: str = "INFO"
    min_drop_percent: float = 1.0


@dataclass
class Config:
    email: EmailConfig
    destinations: list[Destination]
    settings: Settings


def _apply_env_overrides(email: EmailConfig) -> EmailConfig:
    """Variáveis de ambiente têm prioridade (úteis no GitHub Actions)."""
    email.smtp_host = os.getenv("SMTP_HOST", email.smtp_host)
    email.smtp_port = int(os.getenv("SMTP_PORT", email.smtp_port))
    email.username = os.getenv("SMTP_USER", email.username)
    email.password = os.getenv("SMTP_PASSWORD", email.password)
    email.from_addr = os.getenv("SMTP_FROM", email.from_addr or email.username)
    env_to = os.getenv("ALERT_TO")
    if env_to:
        email.to_addrs = [a.strip() for a in env_to.split(",") if a.strip()]
    return email


def load_config(path: str = "config.yaml") -> Config:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise ConfigError(
            f"Arquivo de configuração não encontrado: {path}. "
            "Copie config.yaml.example para config.yaml."
        )

    with cfg_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    # E-mail
    email_raw = raw.get("email", {}) or {}
    email = EmailConfig(
        enabled=email_raw.get("enabled", True),
        smtp_host=email_raw.get("smtp_host", ""),
        smtp_port=int(email_raw.get("smtp_port", 587)),
        use_tls=email_raw.get("use_tls", True),
        username=email_raw.get("username", ""),
        password=email_raw.get("password", ""),
        from_addr=email_raw.get("from_addr", ""),
        to_addrs=list(email_raw.get("to_addrs", []) or []),
    )
    email = _apply_env_overrides(email)

    # Settings
    s_raw = raw.get("settings", {}) or {}
    settings = Settings(
        history_file=s_raw.get("history_file", "data/history.json"),
        log_dir=s_raw.get("log_dir", "logs"),
        log_level=s_raw.get("log_level", "INFO"),
        min_drop_percent=float(s_raw.get("min_drop_percent", 1.0)),
    )

    # Destinos
    dests_raw = raw.get("destinations", []) or []
    if not dests_raw:
        raise ConfigError("Nenhum destino configurado em 'destinations'.")

    destinations: list[Destination] = []
    seen_ids: set[str] = set()
    for i, d in enumerate(dests_raw):
        for key in ("id", "type", "provider"):
            if key not in d:
                raise ConfigError(f"Destino #{i} sem campo obrigatório '{key}'.")
        if d["id"] in seen_ids:
            raise ConfigError(f"ID de destino duplicado: {d['id']}")
        seen_ids.add(d["id"])
        destinations.append(
            Destination(
                id=str(d["id"]),
                type=str(d["type"]),
                name=str(d.get("name", d["id"])),
                provider=str(d["provider"]),
                params=dict(d.get("params", {}) or {}),
                max_price=(
                    float(d["max_price"]) if d.get("max_price") is not None else None
                ),
            )
        )

    log.info("Configuração carregada: %d destino(s).", len(destinations))
    return Config(email=email, destinations=destinations, settings=settings)
