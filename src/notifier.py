"""Envio de alertas por e-mail via SMTP."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

from .config import EmailConfig
from .logger import get_logger

log = get_logger(__name__)


def _build_body(alerts: list[dict[str, Any]]) -> str:
    linhas = ["Foram encontradas ofertas relevantes:\n"]
    for a in alerts:
        linhas.append(f"• {a['name']}")
        linhas.append(f"    Preço: {a['price']:.2f} {a.get('currency', '')}")
        if a.get("previous") is not None:
            linhas.append(f"    Anterior: {a['previous']:.2f} {a.get('currency', '')}")
        linhas.append(f"    Motivo: {a['reason']}")
        if a.get("details"):
            linhas.append(f"    Detalhes: {a['details']}")
        linhas.append("")
    return "\n".join(linhas)


def send_alert(email: EmailConfig, alerts: list[dict[str, Any]]) -> bool:
    """Envia um e-mail com a lista de alertas. Retorna True em sucesso."""
    if not alerts:
        log.info("Nenhum alerta para enviar.")
        return False
    if not email.enabled:
        log.info("E-mail desabilitado na config; pulando envio.")
        return False
    if not (email.smtp_host and email.username and email.password and email.to_addrs):
        log.warning("Config de e-mail incompleta; não foi possível enviar alerta.")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"[Travel Monitor] {len(alerts)} oferta(s) encontrada(s)"
    msg["From"] = email.from_addr or email.username
    msg["To"] = ", ".join(email.to_addrs)
    msg.set_content(_build_body(alerts))

    try:
        with smtplib.SMTP(email.smtp_host, email.smtp_port, timeout=30) as server:
            if email.use_tls:
                server.starttls()
            server.login(email.username, email.password)
            server.send_message(msg)
        log.info("Alerta enviado para %s.", ", ".join(email.to_addrs))
        return True
    except (smtplib.SMTPException, OSError) as exc:
        log.error("Falha ao enviar e-mail: %s", exc)
        return False
