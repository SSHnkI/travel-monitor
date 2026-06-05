"""Ponto de entrada do Travel Monitor.

Uso:
    python main.py                 # usa config.yaml
    python main.py -c outro.yaml   # config alternativa
"""
from __future__ import annotations

import argparse
import sys

from src.config import ConfigError, load_config
from src.logger import get_logger, setup_logging
from src.monitor import run
from src.notifier import send_alert


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Monitor de preços de viagem.")
    p.add_argument("-c", "--config", default="config.yaml", help="Caminho do YAML.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Logging mínimo antes de ler a config (caso a leitura falhe).
    setup_logging(log_dir="logs", level="INFO")
    log = get_logger("main")

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        log.error("Configuração inválida: %s", exc)
        return 2

    # Reconfigura nível/dir de log conforme a config (idempotente).
    setup_logging(config.settings.log_dir, config.settings.log_level)

    try:
        alerts = run(config)
    except Exception as exc:  # rede de segurança final
        log.exception("Falha inesperada durante o monitoramento: %s", exc)
        return 1

    if alerts:
        send_alert(config.email, alerts)
        log.info("Concluído: %d alerta(s).", len(alerts))
    else:
        log.info("Concluído: nenhum alerta desta vez.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
